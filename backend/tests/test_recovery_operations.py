from __future__ import annotations
from decimal import Decimal
import pytest
from app.models.tenancy import UserAccountModel,TenantMembershipModel
from app.models.recovery_operations import RecoveryEvidencePackModel,RecoveryAuditEventModel
from app.services.recovery_operations import RecoveryOperationsService
from app.services.review_workbench import ReviewConflictError,ReviewLockError
from tests.test_appeal_evidence_reconsideration import factory
from tests.test_financial_investigation import seed_case

def setup_recovery(db,key="r",amount=Decimal("250"),remediation_type="recoupment_referral"):
    fin,c=seed_case(db,code="overpayment",key=key);lease=fin.acquire_lease(c.case_id,"finance-op",expected_case_version=1)
    fin.classify_root_cause(c.case_id,"finance-op",root_cause_code="overpayment",rationale="Human financial investigation confirms an evidence-bound overpayment requiring governed recovery operations.",ai_disagreement_rationale=None,expected_case_version=2,lease_token=lease["lease_token"])
    p=fin.propose_remediation(c.case_id,"finance-op",remediation_type=remediation_type,amount=amount,currency="USD",reason_code="verified_overpayment",rationale="Create governed accounting recoupment referral before recovery execution tracking begins.",idempotency_key=f"{key}-prop",lease_token=lease["lease_token"])
    fin.approve_remediation(c.case_id,p.proposal_id,"finance-approver",rationale="Independent finance approver validates material recovery referral.",idempotency_key=f"{key}-approve")
    p=fin.execute_referral(c.case_id,p.proposal_id,"finance-op",lease_token=lease["lease_token"],idempotency_key=f"{key}-exec")
    svc=RecoveryOperationsService(db,"tenant-a");r=svc.create_from_remediation(p.proposal_id,"finance-op",idempotency_key=f"{key}-recovery");return svc,r,p

def add_provider(db):
    if db.get(UserAccountModel,"provider-user") is None:
        db.add(UserAccountModel(user_id="provider-user",external_issuer="https://id.example",external_subject="provider-user",display_name="Provider User",status="active"));db.flush();db.add(TenantMembershipModel(membership_id="m-provider-user",tenant_id="tenant-a",user_id="provider-user",role="provider",status="active",provider_organization_id="org-a"));db.flush()

def test_executed_release43_referral_creates_immutable_recovery_case_evidence_and_sla():
    f=factory()
    with f() as db:
        svc,c,p=setup_recovery(db,"create")
        pack=svc.repo.pack(c.recovery_case_id);assert pack and len(pack.payload_sha256)==64 and pack.source_sha256==p.payload_sha256
        assert c.source_proposal_id==p.proposal_id and c.referral_id==p.referral_id and c.recovery_type=="recoupment_recovery"
        assert svc.repo.tasks(c.recovery_case_id)[0].task_type=="recovery_verification"
        assert db.query(RecoveryEvidencePackModel).count()==1

def test_remediation_verification_and_partial_multi_recovery_are_evidence_only_not_money_movement():
    f=factory()
    with f() as db:
        svc,c,_=setup_recovery(db,"partial",Decimal("250"));lease=svc.acquire_lease(c.recovery_case_id,"finance-op",expected_case_version=1)
        v=svc.verify_remediation_outcome(c.recovery_case_id,"finance-op",lease_token=lease["lease_token"],idempotency_key="verify-partial");assert v.source_type=="accounting_recoupment_request" and v.status=="pending_approval"
        svc.record_recovery(c.recovery_case_id,"finance-op",amount=Decimal("100"),currency="USD",external_reference="bank-rec-1",evidence_details={"receipt_sha256":"a"*64},lease_token=lease["lease_token"],idempotency_key="recover-1")
        svc.record_recovery(c.recovery_case_id,"finance-op",amount=Decimal("150"),currency="USD",external_reference="bank-rec-2",evidence_details={"receipt_sha256":"b"*64},lease_token=lease["lease_token"],idempotency_key="recover-2")
        c=svc.repo.case(c.recovery_case_id);assert c.recovered_amount==Decimal("250") and c.status=="recovered" and c.effectiveness_score==100
        assert len(svc.repo.outcomes(c.recovery_case_id))==3

def test_provider_dispute_is_evidence_bound_material_and_legacy_direct_resolution_is_retired():
    f=factory()
    with f() as db:
        svc,c,_=setup_recovery(db,"dispute",Decimal("250"));add_provider(db);svc.acquire_lease(c.recovery_case_id,"finance-op",expected_case_version=1)
        d=svc.submit_dispute(c.recovery_case_id,"provider-user",external_reference="PD-44-1",disputed_amount=Decimal("200"),currency="USD",reason_code="amount_disputed",statement="Provider disputes the recovery amount and supplies supporting remittance evidence for independent human review.",evidence_refs=["provider-remittance-1"],idempotency_key="provider-dispute")
        assert d.material and d.status=="escalated" and len(d.evidence_pack_sha256)==64
        with pytest.raises(ReviewConflictError,match="retired"):svc.resolve_dispute(c.recovery_case_id,d.dispute_id,"finance-approver",outcome="reduce_recovery",rationale="Legacy direct resolution is superseded by the evidence-bound packet workflow.",resolution_amount=Decimal("100"),idempotency_key="legacy-resolve")

def test_open_provider_dispute_blocks_recovery_closure_until_new_governed_resolution_workflow_completes():
    f=factory()
    with f() as db:
        svc,c,_=setup_recovery(db,"close",Decimal("125"));add_provider(db);lease=svc.acquire_lease(c.recovery_case_id,"finance-op",expected_case_version=1)
        svc.verify_remediation_outcome(c.recovery_case_id,"finance-op",lease_token=lease["lease_token"],idempotency_key="close-verify")
        svc.submit_dispute(c.recovery_case_id,"provider-user",external_reference="PD-44-C",disputed_amount=Decimal("125"),currency="USD",reason_code="recovery_not_owed",statement="Provider contests the proposed recovery and requests independent human review before the recovery case can close.",evidence_refs=[],idempotency_key="close-dispute")
        current=svc.repo.case(c.recovery_case_id)
        with pytest.raises(ReviewConflictError):svc.close_case(c.recovery_case_id,"finance-op",reason_code="provider_dispute_resolved",rationale="Closure must fail while the provider dispute is unresolved.",expected_case_version=current.case_version,lease_token=lease["lease_token"],idempotency_key="blocked-close")

def test_recovery_correspondence_portfolio_and_traceability_preserve_provenance():
    f=factory()
    with f() as db:
        svc,c,_=setup_recovery(db,"trace",Decimal("80"));lease=svc.acquire_lease(c.recovery_case_id,"finance-op",expected_case_version=1)
        svc.verify_remediation_outcome(c.recovery_case_id,"finance-op",lease_token=lease["lease_token"],idempotency_key="trace-verify")
        corr=svc.add_correspondence(c.recovery_case_id,"finance-op",dispute_id=None,direction="outbound",channel="portal",subject="Recovery verification notice",body="Human finance operations recorded a recovery-status communication without changing adjudication or moving funds.",external_message_id="MSG-44-1",idempotency_key="trace-corr")
        wb=svc.workbench(c.recovery_case_id,"finance-op");assert wb["correspondence"][0]["body_sha256"] and corr.body
        portfolio=svc.portfolio("finance-op");assert portfolio["cases"]==1 and portfolio["authority"]=="analytics_only"
        trace=svc.traceability(c.recovery_case_id,"finance-op");assert trace["upstream_anomaly_investigation_remediation"] and trace["downstream_state"]["source_type"]=="accounting_recoupment_request"
        assert trace["authority"]["automation_collects_or_moves_funds"] is False


def test_payment_hold_lifecycle_verification_reads_existing_release40_control_without_releasing_it():
    f=factory()
    with f() as db:
        svc,c,p=setup_recovery(db,"hold44",Decimal("1000"),"payment_hold");lease=svc.acquire_lease(c.recovery_case_id,"finance-op",expected_case_version=1)
        out=svc.verify_remediation_outcome(c.recovery_case_id,"finance-op",lease_token=lease["lease_token"],idempotency_key="hold44-verify")
        assert c.recovery_type=="payment_hold_verification" and out.status=="active" and out.details["verified"] is True
        from app.models.financial_handoff import PaymentHoldModel
        assert db.get(PaymentHoldModel,p.referral_id).active is True

def test_void_reissue_outcome_tracking_observes_governed_release40_request_only():
    f=factory()
    with f() as db:
        svc,c,p=setup_recovery(db,"void44",Decimal("1000"),"void_reissue_referral");lease=svc.acquire_lease(c.recovery_case_id,"finance-op",expected_case_version=1)
        out=svc.verify_remediation_outcome(c.recovery_case_id,"finance-op",lease_token=lease["lease_token"],idempotency_key="void44-verify")
        assert c.recovery_type=="void_reissue_verification" and out.source_type=="void_reissue_request" and out.status=="pending_approval"
        assert out.amount==Decimal("0")

def test_release44_authority_worker_and_database_contract_fail_closed():
    from pathlib import Path
    root=Path(__file__).resolve().parents[2];domain=(root/'backend/app/domain/recovery_operations.py').read_text();migration=(root/'backend/alembic/versions/0039_recovery_operations_provider_disputes.py').read_text();worker=(root/'backend/app/workers/recovery_operations.py').read_text()
    for token in ['"ai_can_adjudicate_provider_dispute": False','"ai_can_approve_accounting_change": False','"ai_can_authorize_payment": False','"ai_can_collect_funds": False','"background_worker_can_move_money": False','"independent_human_dispute_resolution_required": True']:assert token in domain
    for forbidden in ['resolve_dispute(', 'record_recovery(', 'close_case(', 'approve_adjustment(', 'authorize_packet(', 'handoff(', '_post_journal(']:assert forbidden not in worker
    assert 'ENABLE ROW LEVEL SECURITY' in migration and 'FORCE ROW LEVEL SECURITY' in migration and 'reject_recovery_immutable_mutation' in migration
