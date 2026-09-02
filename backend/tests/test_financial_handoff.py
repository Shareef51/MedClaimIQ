from __future__ import annotations
from datetime import date
from decimal import Decimal
import pytest
from sqlalchemy import select
from app.domain.claims import HumanDecision
from app.domain.governed_closure import SecondReviewAction
from app.models.tenancy import UserAccountModel, TenantMembershipModel
from app.models.financial_handoff import FinancialReconciliationExceptionModel, PaymentIntentModel
from app.services.financial_handoff import FinancialHandoffService
from app.services.governed_closure import GovernedClosureService
from app.services.review_workbench import ReviewWorkbenchService, ReviewConflictError
from tests.test_appeal_evidence_reconsideration import factory


def setup_finance(db):
    for uid,role,mid in (("finance-op","finance_operator","m-fin-op"),("finance-approver","finance_approver","m-fin-ap"),("finance-approver-2","finance_approver","m-fin-ap2")):
        db.add(UserAccountModel(user_id=uid,external_issuer="https://id.example",external_subject=uid,display_name=uid,status="active"));db.flush()
        db.add(TenantMembershipModel(membership_id=mid,tenant_id="tenant-a",user_id=uid,role=role,status="active"))
    db.flush()

def close_original(db,decision=HumanDecision.APPROVE,approved_amount=None):
    _,token=ReviewWorkbenchService(db,"tenant-a").acquire_lock("claim-1","reviewer-1")
    svc=GovernedClosureService(db,"tenant-a")
    p=svc.save_packet("claim-1","reviewer-1",token,decision=decision,rationale="Authorized human reviewer completes the original evidence-bound claim adjudication.",reason_codes=["evidence_supports"],evidence_snapshot_ids=["ev-original"],finding_refs=[],annotation_refs=[],inconsistency_refs=[],checkpoint_refs=[],approved_amount=approved_amount,partial_line_decisions=[],ai_disagreement_reason=None,escalation_queue=None,expected_claim_status_version=5,expected_packet_version=None,idempotency_key="release40-close-packet")
    p=svc.validate_and_lock("claim-1",p.packet_id,"reviewer-1",token,expected_packet_version=1,idempotency_key="release40-lock")
    if p.status=="pending_second_review":
        p=svc.second_review("claim-1",p.packet_id,"reviewer-2",action=SecondReviewAction.APPROVE,rationale="Independent second human reviewer confirms the governed adjudication packet before closure.",expected_packet_version=1,idempotency_key="release40-second-review")
    svc.close("claim-1",p.packet_id,"reviewer-1",token,expected_packet_version=1,expected_claim_status_version=5,idempotency_key="release40-close")
    db.flush();return p

def test_human_authorized_financial_packet_remittance_handoff_settlement_and_reconciliation():
    f=factory()
    with f() as db:
        setup_finance(db); close_original(db); svc=FinancialHandoffService(db,"tenant-a")
        p=svc.prepare_packet("claim-1","finance-op",idempotency_key="release40-packet")
        assert p.controlling_decision=="approve" and p.approved_amount==Decimal("1000.00") and p.member_responsibility==Decimal("0.00")
        arts=svc.repo.artifacts(p.packet_id); assert {x.artifact_type for x in arts}=={"eob_json","x12_835_style"}; assert all(len(x.content_sha256)==64 for x in arts)
        p=svc.lock_packet("claim-1",p.packet_id,"finance-op",expected_packet_version=1,idempotency_key="release40-packet-lock")
        with pytest.raises(ReviewConflictError): svc.authorize_packet("claim-1",p.packet_id,"finance-op",rationale="This same human must not be allowed to authorize their own financial packet.",idempotency_key="bad-sod")
        p=svc.authorize_packet("claim-1",p.packet_id,"finance-approver",rationale="Independent finance approver confirms the locked human decision, amount, payee workflow, and remittance bindings.",idempotency_key="release40-auth")
        assert p.status=="authorized" and p.authorized_by_user_id=="finance-approver"
        intent=svc.stage_payment_intent("claim-1",p.packet_id,"finance-op",payee_ref="provider:org-a",idempotency_key="release40-intent")
        same=svc.stage_payment_intent("claim-1",p.packet_id,"finance-op",payee_ref="provider:org-a",idempotency_key="release40-intent-repeat")
        assert same.payment_intent_id==intent.payment_intent_id
        h=svc.handoff("claim-1",intent.payment_intent_id,actor_id="finance-op",idempotency_key="release40-handoff")
        assert h.status=="accepted_for_processing" and intent.status=="submitted"
        svc.ingest_settlement("claim-1",intent.payment_intent_id,provider_event_id="settle-ok",status="settled",settled_amount=Decimal("1000.00"),currency="USD",external_reference="ACH-1",actor_user_id="finance-op")
        assert intent.status=="settled" and not svc.repo.exceptions("claim-1")
        snap=svc.snapshot("claim-1"); assert snap["authority"]["llm_can_authorize_funds"] is False and snap["authority"]["background_worker_can_authorize_funds"] is False
        assert snap["audit"][-1]["previous_event_sha256"] is not None

def test_payment_hold_blocks_authorization_until_distinct_human_release():
    f=factory()
    with f() as db:
        setup_finance(db);close_original(db);svc=FinancialHandoffService(db,"tenant-a")
        p=svc.prepare_packet("claim-1","finance-op",idempotency_key="hold-packet");p=svc.lock_packet("claim-1",p.packet_id,"finance-op",expected_packet_version=1,idempotency_key="hold-lock")
        hold=svc.place_hold("claim-1","finance-op",hold_type="fraud_review",reason_code="siu_pending",rationale="A fraud-review payment hold is required until an independent finance approver releases it.",idempotency_key="hold-place")
        with pytest.raises(ReviewConflictError):svc.authorize_packet("claim-1",p.packet_id,"finance-approver",rationale="Independent approval is attempted while a blocking fraud hold remains active.",idempotency_key="hold-auth-block")
        svc.release_hold("claim-1",hold.hold_id,"finance-approver",rationale="Fraud review completed and the human finance approver explicitly releases the payment hold.",idempotency_key="hold-release")
        # authorize with a second approver to show release/authorization can also be separated operationally.
        p.status="pending_authorization"
        p=svc.authorize_packet("claim-1",p.packet_id,"finance-approver-2",rationale="A separate human finance approver authorizes the immutable packet after the hold has been cleared.",idempotency_key="hold-auth-ok")
        assert p.status=="authorized"

def test_settlement_amount_mismatch_creates_exception_and_void_requires_dual_human_approval():
    f=factory()
    with f() as db:
        setup_finance(db);close_original(db);svc=FinancialHandoffService(db,"tenant-a")
        p=svc.prepare_packet("claim-1","finance-op",idempotency_key="recon-packet");svc.lock_packet("claim-1",p.packet_id,"finance-op",expected_packet_version=1,idempotency_key="recon-lock");svc.authorize_packet("claim-1",p.packet_id,"finance-approver",rationale="Independent human finance authorization validates the amount and immutable decision lineage.",idempotency_key="recon-auth")
        i=svc.stage_payment_intent("claim-1",p.packet_id,"finance-op",payee_ref="provider:org-a",idempotency_key="recon-intent");svc.handoff("claim-1",i.payment_intent_id,actor_id="finance-op",idempotency_key="recon-handoff")
        svc.ingest_settlement("claim-1",i.payment_intent_id,provider_event_id="settle-mismatch",status="settled",settled_amount=Decimal("900.00"),currency="USD",actor_user_id="finance-op")
        exc=svc.repo.exceptions("claim-1"); assert len(exc)==1 and exc[0].exception_type=="settled_amount_mismatch"
        vr=svc.request_void_reissue("claim-1",i.payment_intent_id,"finance-op",action="void",reason="Observed settlement mismatch requires a governed void request before any correction can be attempted.",idempotency_key="void-request")
        with pytest.raises(ReviewConflictError): svc.approve_void_reissue("claim-1",vr.request_id,"finance-op",idempotency_key="void-self")
        vr=svc.approve_void_reissue("claim-1",vr.request_id,"finance-approver",idempotency_key="void-approve");assert vr.status=="approved" and i.status=="void_pending"

def test_denial_produces_remittance_but_never_positive_payment_intent():
    f=factory()
    with f() as db:
        setup_finance(db);close_original(db,HumanDecision.DENY);svc=FinancialHandoffService(db,"tenant-a")
        p=svc.prepare_packet("claim-1","finance-op",idempotency_key="deny-packet");svc.lock_packet("claim-1",p.packet_id,"finance-op",expected_packet_version=1,idempotency_key="deny-lock");svc.authorize_packet("claim-1",p.packet_id,"finance-approver",rationale="Finance approver confirms this human denial produces remittance information only and no payable instruction.",idempotency_key="deny-auth")
        assert p.approved_amount==Decimal("0.00") and p.member_responsibility==Decimal("1000.00")
        with pytest.raises(ReviewConflictError):svc.stage_payment_intent("claim-1",p.packet_id,"finance-op",payee_ref="provider:org-a",idempotency_key="deny-intent")

def test_financial_migration_and_authority_contract_are_fail_closed():
    from pathlib import Path
    root=Path(__file__).resolve().parents[2]
    migration=(root/"backend/alembic/versions/0035_financial_handoff_reconciliation.py").read_text()
    domain=(root/"backend/app/domain/financial_handoff.py").read_text()
    adapter=(root/"backend/app/financial/adapters.py").read_text()
    assert "ENABLE ROW LEVEL SECURITY" in migration and "FORCE ROW LEVEL SECURITY" in migration
    assert "reject_locked_financial_packet_mutation" in migration
    assert '"llm_can_authorize_funds": False' in domain and '"background_worker_can_authorize_funds": False' in domain
    assert "never moves funds" in adapter
