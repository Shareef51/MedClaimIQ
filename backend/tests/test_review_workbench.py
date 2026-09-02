from __future__ import annotations
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
import hashlib
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app import models  # noqa
from app.db.base import Base
from app.domain.claims import HumanDecision
from app.domain.review_workbench import ReviewPriorityInputs, ReviewPriorityBand, calculate_priority
from app.models.claims import ClaimModel, EvidenceArtifactModel
from app.models.review_workbench import ReviewActionEventModel, ReviewClaimLockModel, ReviewDecisionMetadataModel, ReviewerNoteModel
from app.models.tenancy import OrganizationModel, TenantMembershipModel, TenantModel, UserAccountModel
from app.services.review_workbench import ReviewConflictError, ReviewLockError, ReviewWorkbenchService


def factory():
    engine=create_engine("sqlite+pysqlite:///:memory:",future=True)
    Base.metadata.create_all(engine)
    f=sessionmaker(bind=engine,autoflush=False,expire_on_commit=False)
    with f() as db:
        db.add(TenantModel(tenant_id="tenant-a",slug="tenant-a",display_name="Tenant A",tenant_type="payer",status="active",data_region="local"))
        db.add(OrganizationModel(organization_id="org-a",tenant_id="tenant-a",slug="org-a",display_name="Org A",organization_type="payer",external_identifiers={},is_active=True))
        for uid in ("reviewer-1","reviewer-2"):
            db.add(UserAccountModel(user_id=uid,external_issuer="https://id.example",external_subject=uid,display_name=uid,status="active"))
        db.flush()
        for i,uid in enumerate(("reviewer-1","reviewer-2"),1):
            db.add(TenantMembershipModel(membership_id=f"m-{i}",tenant_id="tenant-a",user_id=uid,role="claims_reviewer",status="active"))
        db.add(ClaimModel(claim_id="claim-1",tenant_id="tenant-a",external_claim_ref="EXT-1",patient_subject_id="patient-1",provider_organization_id="org-a",payer_organization_id="org-a",claim_type="medical",status="human_review",status_version=8,total_amount=Decimal("15000"),currency="USD",service_from=date(2026,8,1)))
        db.add(EvidenceArtifactModel(evidence_id="ev-1",tenant_id="tenant-a",claim_id="claim-1",patient_subject_id="patient-1",source_type="synthetic_fixture",source_system="test",source_locator={"page":1},document_type="eob",media_type="application/pdf",object_key="accepted/ev-1.pdf",content_sha256="a"*64,byte_size=100,status="ready",evidence_version=1,authoritative=True,media_metadata={}))
        db.commit()
    return f


def test_priority_is_deterministic_and_explainable():
    score, band, reasons=calculate_priority(ReviewPriorityInputs(claim_status="human_review",overdue_timers=1,critical_sla_items=1,material_contradictions=1,claim_amount=15000))
    assert score == 100 and band is ReviewPriorityBand.CRITICAL
    assert {"human_review","overdue_sla","critical_sla","material_contradiction","high_value_claim"}.issubset(reasons)


def test_lock_persists_only_hash_and_blocks_second_reviewer():
    f=factory()
    with f() as db:
        svc=ReviewWorkbenchService(db,"tenant-a")
        row,token=svc.acquire_lock("claim-1","reviewer-1",lease_seconds=300); db.commit()
        assert row.lock_token_sha256 == hashlib.sha256(token.encode()).hexdigest() and token != row.lock_token_sha256
        with pytest.raises(ReviewConflictError): svc.acquire_lock("claim-1","reviewer-2")


def test_wrong_lock_token_fails_closed():
    f=factory()
    with f() as db:
        svc=ReviewWorkbenchService(db,"tenant-a"); svc.acquire_lock("claim-1","reviewer-1")
        with pytest.raises(ReviewLockError): svc.verify_lock("claim-1","reviewer-1","wrong-token")


def test_expired_lock_can_be_reacquired_by_same_assigned_reviewer():
    f=factory(); now=datetime(2026,8,20,12,0,tzinfo=UTC)
    with f() as db:
        svc=ReviewWorkbenchService(db,"tenant-a")
        first,_=svc.acquire_lock("claim-1","reviewer-1",lease_seconds=60,now=now)
        second,_=svc.acquire_lock("claim-1","reviewer-1",lease_seconds=60,now=now+timedelta(seconds=61))
        assert second.lock_version == first.lock_version and second.lock_version == 2


def test_reviewer_note_is_evidence_linked_and_audited():
    f=factory()
    with f() as db:
        svc=ReviewWorkbenchService(db,"tenant-a"); _,token=svc.acquire_lock("claim-1","reviewer-1")
        note=svc.add_note("claim-1","reviewer-1",token,note_type="evidence",body="Synthetic note",evidence_refs=["ev-1"],idempotency_key="note-key-123")
        db.commit()
        assert note.body_sha256 == hashlib.sha256(b"Synthetic note").hexdigest()
        assert db.scalar(select(ReviewActionEventModel).where(ReviewActionEventModel.event_type=="review.note.added")) is not None


def test_final_decision_requires_current_status_version_and_persists_metadata():
    f=factory()
    with f() as db:
        svc=ReviewWorkbenchService(db,"tenant-a"); _,token=svc.acquire_lock("claim-1","reviewer-1")
        with pytest.raises(ReviewConflictError):
            svc.record_decision("claim-1","reviewer-1",token,decision=HumanDecision.APPROVE,rationale="Synthetic rationale",reason_codes=["evidence_supports"],evidence_snapshot_ids=["ev-1"],expected_claim_status_version=7,override_reason=None,idempotency_key="decision-old-123")
        result=svc.record_decision("claim-1","reviewer-1",token,decision=HumanDecision.APPROVE,rationale="Synthetic rationale",reason_codes=["evidence_supports"],evidence_snapshot_ids=["ev-1"],expected_claim_status_version=8,override_reason=None,idempotency_key="decision-good-123")
        db.commit()
        meta=db.scalar(select(ReviewDecisionMetadataModel).where(ReviewDecisionMetadataModel.decision_id==result.decision_id))
        assert meta.reason_codes == ["evidence_supports"]
        assert db.scalar(select(ClaimModel).where(ClaimModel.claim_id=="claim-1")).status == "completed"


def test_migration_has_rls_and_immutable_review_audit():
    text=Path("alembic/versions/0017_human_review_workbench.py").read_text() if Path("alembic/versions/0017_human_review_workbench.py").exists() else Path("backend/alembic/versions/0017_human_review_workbench.py").read_text()
    assert "FORCE ROW LEVEL SECURITY" in text
    assert 'IMMUTABLE = ("reviewer_notes", "review_action_events", "review_decision_metadata")' in text
    assert "lock_token_sha256" in text and "expected_claim_status_version" in text

def test_ai_disagreement_requires_human_override_reason(monkeypatch):
    f=factory()
    with f() as db:
        svc=ReviewWorkbenchService(db,"tenant-a"); _,token=svc.acquire_lock("claim-1","reviewer-1")
        monkeypatch.setattr(svc,"latest_ai_recommendation",lambda claim_id:"support_denial")
        with pytest.raises(ReviewConflictError):
            svc.record_decision("claim-1","reviewer-1",token,decision=HumanDecision.APPROVE,rationale="Reviewer evidence rationale",reason_codes=["human_judgment"],evidence_snapshot_ids=["ev-1"],expected_claim_status_version=8,override_reason=None,idempotency_key="override-missing-123")
        result=svc.record_decision("claim-1","reviewer-1",token,decision=HumanDecision.APPROVE,rationale="Reviewer evidence rationale",reason_codes=["human_judgment"],evidence_snapshot_ids=["ev-1"],expected_claim_status_version=8,override_reason="Authoritative source evidence supports the human conclusion.",idempotency_key="override-good-123")
        db.commit()
        meta=db.scalar(select(ReviewDecisionMetadataModel).where(ReviewDecisionMetadataModel.decision_id==result.decision_id))
        assert meta.override_ai_recommendation is True
        assert meta.ai_recommendation == "support_denial"


def test_request_more_evidence_uses_canonical_human_decision_lifecycle():
    f=factory()
    with f() as db:
        svc=ReviewWorkbenchService(db,"tenant-a"); _,token=svc.acquire_lock("claim-1","reviewer-1")
        result=svc.request_more_evidence("claim-1","reviewer-1",token,rationale="Need additional synthetic invoice evidence",requested_document_types=["invoice"],evidence_snapshot_ids=["ev-1"],idempotency_key="request-info-123")
        db.commit()
        claim=db.scalar(select(ClaimModel).where(ClaimModel.claim_id=="claim-1"))
        assert result.decision == "request_information"
        assert claim.status == "pending_evidence"
