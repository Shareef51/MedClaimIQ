from __future__ import annotations
from datetime import date
from decimal import Decimal
from pathlib import Path
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app import models  # noqa
from app.db.base import Base
from app.domain.claims import HumanDecision
from app.domain.governed_closure import SecondReviewAction
from app.models.claims import ClaimLineModel, ClaimModel, EvidenceArtifactModel
from app.models.evidence_graph import EvidenceContradictionModel
from app.models.governed_closure import AdjudicationAuditEventModel, DecisionNotificationIntentModel, ReviewDecisionPacketModel
from app.models.tenancy import OrganizationModel, TenantMembershipModel, TenantModel, UserAccountModel
from app.services.governed_closure import GovernedClosureService
from app.services.review_workbench import ReviewConflictError, ReviewWorkbenchService


def factory(total: str="150.00"):
    engine=create_engine("sqlite+pysqlite:///:memory:",future=True)
    Base.metadata.create_all(engine)
    f=sessionmaker(bind=engine,autoflush=False,expire_on_commit=False)
    with f() as db:
        db.add(TenantModel(tenant_id="tenant-a",slug="tenant-a",display_name="Tenant A",tenant_type="payer",status="active",data_region="local"))
        db.add(OrganizationModel(organization_id="org-a",tenant_id="tenant-a",slug="org-a",display_name="Org A",organization_type="payer",external_identifiers={},is_active=True))
        for uid in ("reviewer-1","reviewer-2","agent-user"):
            db.add(UserAccountModel(user_id=uid,external_issuer="https://id.example",external_subject=uid,display_name=uid,status="active"))
        db.flush()
        db.add(TenantMembershipModel(membership_id="m-1",tenant_id="tenant-a",user_id="reviewer-1",role="claims_reviewer",status="active"))
        db.add(TenantMembershipModel(membership_id="m-2",tenant_id="tenant-a",user_id="reviewer-2",role="claims_reviewer",status="active"))
        db.add(ClaimModel(claim_id="claim-1",tenant_id="tenant-a",external_claim_ref="EXT-1",patient_subject_id="p1",provider_organization_id="org-a",payer_organization_id="org-a",claim_type="medical",status="human_review",status_version=5,total_amount=Decimal(total),currency="USD",service_from=date(2026,8,1)))
        db.add(ClaimLineModel(claim_line_id="line-1",tenant_id="tenant-a",claim_id="claim-1",line_number=1,code_system="CPT",service_code="99213",description="Synthetic",service_date=date(2026,8,1),units=Decimal("1"),amount=Decimal(total),provider_id=None))
        db.add(EvidenceArtifactModel(evidence_id="ev-1",tenant_id="tenant-a",claim_id="claim-1",patient_subject_id="p1",source_type="synthetic_fixture",source_system="test",source_locator={"page":1},document_type="eob",media_type="application/pdf",object_key="accepted/ev-1.pdf",content_sha256="a"*64,byte_size=100,status="ready",evidence_version=1,authoritative=True,media_metadata={}))
        db.commit()
    return f


def save_basic(svc, token, *, decision=HumanDecision.APPROVE, approved_amount=None, lines=None, disagreement=None, escalation_queue=None, expected_packet_version=None, key="packet-create-123"):
    return svc.save_packet("claim-1","reviewer-1",token,decision=decision,rationale="Authoritative synthetic evidence supports this human conclusion.",reason_codes=["evidence_supports"],evidence_snapshot_ids=["ev-1"],finding_refs=[],annotation_refs=[],inconsistency_refs=[],checkpoint_refs=[],approved_amount=approved_amount,partial_line_decisions=lines or [],ai_disagreement_reason=disagreement,escalation_queue=escalation_queue,expected_claim_status_version=5,expected_packet_version=expected_packet_version,idempotency_key=key)


def test_low_value_packet_validates_closes_and_emits_immutable_provenance():
    f=factory()
    with f() as db:
        _,token=ReviewWorkbenchService(db,"tenant-a").acquire_lock("claim-1","reviewer-1")
        svc=GovernedClosureService(db,"tenant-a")
        packet=save_basic(svc,token)
        assert packet.packet_version==1 and packet.evidence_snapshot_sha256
        packet=svc.validate_and_lock("claim-1",packet.packet_id,"reviewer-1",token,expected_packet_version=1,idempotency_key="validate-123")
        assert packet.status=="ready_to_close" and packet.dual_control_required is False and packet.locked_payload_sha256
        packet=svc.close("claim-1",packet.packet_id,"reviewer-1",token,expected_packet_version=1,expected_claim_status_version=5,idempotency_key="close-123")
        db.commit()
        assert packet.status=="closed" and packet.decision_id
        assert db.scalar(select(ClaimModel).where(ClaimModel.claim_id=="claim-1")).status=="completed"
        audits=list(db.scalars(select(AdjudicationAuditEventModel).order_by(AdjudicationAuditEventModel.sequence)))
        assert [x.event_type for x in audits]==["adjudication.packet.created","adjudication.packet.validated","adjudication.claim.closed"]
        assert audits[1].previous_event_sha256==audits[0].event_sha256
        assert len(list(db.scalars(select(DecisionNotificationIntentModel))))==3


def test_high_value_claim_requires_distinct_second_reviewer_before_closure():
    f=factory("15000.00")
    with f() as db:
        _,token=ReviewWorkbenchService(db,"tenant-a").acquire_lock("claim-1","reviewer-1")
        svc=GovernedClosureService(db,"tenant-a"); packet=save_basic(svc,token)
        packet=svc.validate_and_lock("claim-1",packet.packet_id,"reviewer-1",token,expected_packet_version=1,idempotency_key="validate-high")
        assert packet.status=="pending_second_review" and packet.dual_control_required is True
        with pytest.raises(ReviewConflictError):
            svc.second_review("claim-1",packet.packet_id,"reviewer-1",action=SecondReviewAction.APPROVE,rationale="Primary reviewer cannot self-approve dual control.",expected_packet_version=1,idempotency_key="self-review")
        packet=svc.second_review("claim-1",packet.packet_id,"reviewer-2",action=SecondReviewAction.APPROVE,rationale="Independent reviewer confirms the evidence-bound packet.",expected_packet_version=1,idempotency_key="second-review")
        assert packet.status=="ready_to_close" and packet.second_reviewer_user_id=="reviewer-2"
        svc.close("claim-1",packet.packet_id,"reviewer-1",token,expected_packet_version=1,expected_claim_status_version=5,idempotency_key="close-high")
        db.commit()
        assert db.scalar(select(ClaimModel).where(ClaimModel.claim_id=="claim-1")).status=="completed"


def test_open_material_conflict_blocks_financial_decision_validation():
    f=factory()
    with f() as db:
        db.add(EvidenceContradictionModel(contradiction_id="contra-1",tenant_id="tenant-a",claim_id="claim-1",subject_entity_id=None,field_name="amount",left_mapping_id="map-left",right_mapping_id="map-right",left_value={"amount":"150"},right_value={"amount":"900"},severity="material",confidence=Decimal("0.95"),status="open",contradiction_fingerprint="f"*64,resolution=None,resolved_by_user_id=None,resolved_at=None))
        db.flush(); _,token=ReviewWorkbenchService(db,"tenant-a").acquire_lock("claim-1","reviewer-1")
        svc=GovernedClosureService(db,"tenant-a"); packet=save_basic(svc,token)
        with pytest.raises(ReviewConflictError,match="material_graph_conflict"):
            svc.validate_and_lock("claim-1",packet.packet_id,"reviewer-1",token,expected_packet_version=1,idempotency_key="validate-blocked")


def test_partial_approval_binds_approved_and_denied_amounts_and_requires_dual_control():
    f=factory("1000.00")
    with f() as db:
        _,token=ReviewWorkbenchService(db,"tenant-a").acquire_lock("claim-1","reviewer-1")
        svc=GovernedClosureService(db,"tenant-a")
        packet=save_basic(svc,token,decision=HumanDecision.PARTIAL_APPROVE,approved_amount=Decimal("600"),lines=[{"claim_line_id":"line-1","outcome":"approve","amount":"600","reason_code":"evidence_supports"}],key="partial-create")
        assert Decimal(str(packet.approved_amount))==Decimal("600.00") and Decimal(str(packet.denied_amount))==Decimal("400.00")
        packet=svc.validate_and_lock("claim-1",packet.packet_id,"reviewer-1",token,expected_packet_version=1,idempotency_key="partial-validate")
        assert packet.dual_control_required and packet.status=="pending_second_review"


def test_non_reviewer_cannot_author_or_close_packet_even_if_user_exists():
    f=factory()
    with f() as db:
        _,token=ReviewWorkbenchService(db,"tenant-a").acquire_lock("claim-1","reviewer-1")
        svc=GovernedClosureService(db,"tenant-a")
        with pytest.raises(ReviewConflictError,match="active human claims reviewer"):
            svc.save_packet("claim-1","agent-user",token,decision=HumanDecision.APPROVE,rationale="An automated actor must never adjudicate this claim.",reason_codes=["human_judgment"],evidence_snapshot_ids=["ev-1"],finding_refs=[],annotation_refs=[],inconsistency_refs=[],checkpoint_refs=[],approved_amount=None,partial_line_decisions=[],ai_disagreement_reason=None,escalation_queue=None,expected_claim_status_version=5,expected_packet_version=None,idempotency_key="agent-attempt")


def test_traceability_exposes_human_only_boundary():
    f=factory()
    with f() as db:
        _,token=ReviewWorkbenchService(db,"tenant-a").acquire_lock("claim-1","reviewer-1")
        svc=GovernedClosureService(db,"tenant-a"); packet=save_basic(svc,token)
        graph=svc.traceability("claim-1",packet.packet_id)
        assert graph["evidence_to_finding_to_annotation_to_human_decision"] is True
        assert graph["final_decision_human_only"] is True
        assert any(e["relationship"]=="bound_to_decision_snapshot" for e in graph["edges"])


def test_migration_enforces_rls_and_immutable_adjudication_events():
    text=Path("alembic/versions/0030_governed_human_claim_closure.py").read_text()
    assert "FORCE ROW LEVEL SECURITY" in text
    assert "adjudication_audit_events_immutable" in text
    assert "decision_second_reviews_immutable" in text
    assert "locked_payload_sha256" in text and "evidence_snapshot_sha256" in text
