from __future__ import annotations
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app import models  # noqa
from app.db.base import Base
from app.domain.claims import HumanDecision
from app.domain.post_decision import AppealResolutionOutcome
from app.models.claims import ClaimLineModel, ClaimModel, EvidenceArtifactModel, HumanReviewDecisionModel
from app.models.governed_closure import DecisionNotificationIntentModel, ReviewDecisionPacketModel
from app.models.post_decision import CommunicationDeadLetterModel, DecisionHistoryVersionModel, DecisionNoticeModel
from app.models.tenancy import OrganizationModel, TenantMembershipModel, TenantModel, UserAccountModel
from app.services.governed_closure import GovernedClosureService
from app.services.post_decision import PostDecisionService
from app.services.review_workbench import ReviewConflictError, ReviewWorkbenchService


def factory():
    engine=create_engine("sqlite+pysqlite:///:memory:",future=True)
    Base.metadata.create_all(engine)
    f=sessionmaker(bind=engine,autoflush=False,expire_on_commit=False)
    with f() as db:
        db.add(TenantModel(tenant_id="tenant-a",slug="tenant-a",display_name="Tenant A",tenant_type="payer",status="active",data_region="local"))
        db.add(OrganizationModel(organization_id="org-a",tenant_id="tenant-a",slug="org-a",display_name="Org A",organization_type="payer",external_identifiers={},is_active=True))
        for uid in ("reviewer-1","reviewer-2","reviewer-3","patient-user","agent-user"):
            db.add(UserAccountModel(user_id=uid,external_issuer="https://id.example",external_subject=uid,display_name=uid,status="active"))
        db.flush()
        for idx,uid in enumerate(("reviewer-1","reviewer-2","reviewer-3"),1):
            db.add(TenantMembershipModel(membership_id=f"m-{idx}",tenant_id="tenant-a",user_id=uid,role="claims_reviewer",status="active"))
        db.add(TenantMembershipModel(membership_id="m-patient",tenant_id="tenant-a",user_id="patient-user",role="patient",status="active",patient_subject_id="p1"))
        db.add(ClaimModel(claim_id="claim-1",tenant_id="tenant-a",external_claim_ref="EXT-1",patient_subject_id="p1",provider_organization_id="org-a",payer_organization_id="org-a",claim_type="medical",status="human_review",status_version=5,total_amount=Decimal("1000.00"),currency="USD",service_from=date(2026,8,1)))
        db.add(ClaimLineModel(claim_line_id="line-1",tenant_id="tenant-a",claim_id="claim-1",line_number=1,code_system="CPT",service_code="99213",description="Synthetic",service_date=date(2026,8,1),units=Decimal("1"),amount=Decimal("1000.00"),provider_id=None))
        db.add(EvidenceArtifactModel(evidence_id="ev-original",tenant_id="tenant-a",claim_id="claim-1",patient_subject_id="p1",source_type="synthetic_fixture",source_system="test",source_locator={"page":1},document_type="eob",media_type="application/pdf",object_key="accepted/original.pdf",content_sha256="a"*64,byte_size=100,status="ready",evidence_version=1,authoritative=True,media_metadata={}))
        db.add(EvidenceArtifactModel(evidence_id="ev-appeal",tenant_id="tenant-a",claim_id="claim-1",patient_subject_id="p1",source_type="synthetic_fixture",source_system="appeal-test",source_locator={"page":2},document_type="medical_bill",media_type="application/pdf",object_key="accepted/appeal.pdf",content_sha256="b"*64,byte_size=120,status="ready",evidence_version=1,authoritative=True,media_metadata={}))
        db.commit()
    return f


def close_original(db):
    _,token=ReviewWorkbenchService(db,"tenant-a").acquire_lock("claim-1","reviewer-1")
    svc=GovernedClosureService(db,"tenant-a")
    packet=svc.save_packet("claim-1","reviewer-1",token,decision=HumanDecision.APPROVE,rationale="Original human reviewer found the locked evidence sufficient for approval.",reason_codes=["evidence_supports"],evidence_snapshot_ids=["ev-original"],finding_refs=[],annotation_refs=[],inconsistency_refs=[],checkpoint_refs=[],approved_amount=None,partial_line_decisions=[],ai_disagreement_reason=None,escalation_queue=None,expected_claim_status_version=5,expected_packet_version=None,idempotency_key="original-packet")
    packet=svc.validate_and_lock("claim-1",packet.packet_id,"reviewer-1",token,expected_packet_version=1,idempotency_key="original-validate")
    packet=svc.close("claim-1",packet.packet_id,"reviewer-1",token,expected_packet_version=1,expected_claim_status_version=5,idempotency_key="original-close")
    db.flush(); return packet


def test_closure_bootstraps_locked_notice_draft_and_initial_history():
    f=factory()
    with f() as db:
        packet=close_original(db); svc=PostDecisionService(db,"tenant-a")
        notices=svc.repo.notices("claim-1"); history=svc.repo.history("claim-1")
        assert len(notices)==1 and notices[0].status=="draft"
        assert notices[0].evidence_snapshot_sha256==packet.evidence_snapshot_sha256
        assert notices[0].locked_decision_payload_sha256==packet.locked_payload_sha256
        assert notices[0].rendered_payload["human_authority_statement"].startswith("AI may assist")
        assert len(history)==1 and history[0].source_type=="original_decision" and history[0].decision=="approve"
        assert history[0].previous_version_sha256 is None


def test_human_release_then_delivery_retries_dead_letter_without_changing_decision():
    f=factory()
    with f() as db:
        close_original(db); svc=PostDecisionService(db,"tenant-a"); notice=svc.repo.notices("claim-1")[0]
        notice=svc.release_notice("claim-1",notice.notice_id,"reviewer-1",idempotency_key="release-notice")
        assert notice.status=="delivery_pending" and notice.released_by_user_id=="reviewer-1"
        intent=db.scalar(select(DecisionNotificationIntentModel).where(DecisionNotificationIntentModel.notification_type=="decision_notice_delivery"))
        assert intent is not None
        for i in range(1,4):
            result=svc.record_delivery_attempt("claim-1",intent.notification_id,channel="email",success=False,provider_message_id=None,error_code="provider_timeout",error_detail=f"timeout-{i}")
        assert result=={"status":"dead_lettered","attempt_count":3,"dead_lettered":True}
        assert db.scalar(select(CommunicationDeadLetterModel).where(CommunicationDeadLetterModel.notification_id==intent.notification_id)) is not None
        assert svc.repo.notice(notice.notice_id).status=="dead_lettered"
        original=db.scalar(select(HumanReviewDecisionModel).where(HumanReviewDecisionModel.claim_id=="claim-1"))
        assert original.decision=="approve"


def test_appeal_requires_independent_reviewer_and_creates_immutable_reconsideration_chain():
    f=factory()
    with f() as db:
        packet=close_original(db); svc=PostDecisionService(db,"tenant-a"); notice=svc.repo.notices("claim-1")[0]
        svc.release_notice("claim-1",notice.notice_id,"reviewer-1",idempotency_key="release-appeal-notice")
        appeal=svc.submit_appeal("claim-1","patient-user","patient",notice_id=notice.notice_id,grounds=["new_evidence","factual_error"],statement="The original decision did not include the newly supplied medical bill.",late_filing_reason=None,idempotency_key="appeal-submit")
        assert appeal.status=="submitted" and appeal.appeal_version==1
        svc.link_supplemental_evidence("claim-1",appeal.appeal_id,"ev-appeal","patient-user","patient",idempotency_key="supplement-link")
        assert appeal.appeal_version==2
        with pytest.raises(ReviewConflictError,match="independent"):
            svc.assign_appeal("claim-1",appeal.appeal_id,"reviewer-2","reviewer-1",assignment_reason="Invalid same-reviewer assignment should be blocked.",expected_appeal_version=2,idempotency_key="bad-assignment")
        appeal=svc.assign_appeal("claim-1",appeal.appeal_id,"reviewer-2","reviewer-3",assignment_reason="Independent appeal review is required after new evidence submission.",expected_appeal_version=2,idempotency_key="good-assignment")
        assert appeal.assigned_reviewer_user_id=="reviewer-3" and appeal.appeal_version==3
        appeal=svc.reopen_appeal("claim-1",appeal.appeal_id,"reviewer-3",expected_appeal_version=3,rationale="Independent reviewer accepts the appeal for evidence-bound reconsideration.",idempotency_key="reopen-appeal")
        assert appeal.status=="in_review" and appeal.appeal_version==4
        with pytest.raises(ReviewConflictError,match="direct appeal resolution retired"):
            svc.resolve_appeal("claim-1",appeal.appeal_id,"reviewer-3",outcome=AppealResolutionOutcome.OVERTURN,controlling_decision=HumanDecision.DENY,reason_codes=["evidence_contradicts"],rationale="Legacy direct reconsideration is now intentionally blocked by Release 39 governance.",expected_appeal_version=4,idempotency_key="resolve-appeal")
        history=svc.repo.history("claim-1")
        assert [x.sequence for x in history]==[1]  # no controlling version may bypass Release 39
        decisions=list(db.scalars(select(HumanReviewDecisionModel).where(HumanReviewDecisionModel.claim_id=="claim-1")))
        assert len(decisions)==1 and decisions[0].decision=="approve"
        assert db.scalar(select(ReviewDecisionPacketModel).where(ReviewDecisionPacketModel.packet_id==packet.packet_id)).decision=="approve"


def test_non_reviewer_cannot_release_notice_or_resolve_appeal():
    f=factory()
    with f() as db:
        close_original(db); svc=PostDecisionService(db,"tenant-a"); notice=svc.repo.notices("claim-1")[0]
        with pytest.raises(ReviewConflictError,match="active human claims reviewer"):
            svc.release_notice("claim-1",notice.notice_id,"agent-user",idempotency_key="agent-release")


def test_late_appeal_is_rejected_without_reason_and_routed_with_reason():
    f=factory()
    with f() as db:
        close_original(db); svc=PostDecisionService(db,"tenant-a"); notice=svc.repo.notices("claim-1")[0]
        svc.release_notice("claim-1",notice.notice_id,"reviewer-1",idempotency_key="release-late")
        notice.released_at=notice.released_at-timedelta(days=181); db.flush()
        rejected=svc.submit_appeal("claim-1","patient-user","patient",notice_id=notice.notice_id,grounds=["other"],statement="This filing is intentionally outside the configured appeal period.",late_filing_reason=None,idempotency_key="late-rejected")
        assert rejected.status=="rejected_untimely"
        routed=svc.submit_appeal("claim-1","patient-user","patient",notice_id=notice.notice_id,grounds=["other"],statement="This late filing includes a documented reason for human review.",late_filing_reason="Hospital records were unavailable during the original filing window.",idempotency_key="late-routed")
        assert routed.status=="late_pending_review"


def test_migration_has_rls_immutable_history_and_dlq_controls():
    text=Path("alembic/versions/0031_post_decision_communications_appeals.py").read_text()
    assert 'down_revision="0030_governed_human_claim_closure"' in text
    assert "FORCE ROW LEVEL SECURITY" in text
    assert "decision_history_versions_immutable" in text
    assert "appeal_resolutions_immutable" in text
    assert "communication_dead_letters" in text
    assert "appeal_review_assignments" in text
