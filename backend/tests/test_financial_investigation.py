from __future__ import annotations
from decimal import Decimal
import pytest
from app.models.financial_intelligence import FinancialAnomalyInvestigationModel
from app.models.financial_investigation import FinancialInvestigationEvidencePackModel,FinancialInvestigationAuditEventModel
from app.models.financial_handoff import PaymentHoldModel
from app.models.accounting_ledger import AccountingAdjustmentModel
from app.services.financial_investigation import FinancialInvestigationService
from app.services.review_workbench import ReviewConflictError,ReviewLockError
from tests.test_accounting_ledger import paid_intent
from tests.test_appeal_evidence_reconsideration import factory

def seed_case(db,*,code="returned_payment",score=82,key="case"):
    paid_intent(db,key)
    inv=FinancialAnomalyInvestigationModel(investigation_id=f"fininv-{key}",tenant_id="tenant-a",claim_id="claim-1",anomaly_code=code,anomaly_score=score,severity="critical" if score>=80 else "high",explanation="Deterministic Release 42 anomaly with governed financial citations.",factors=[{"factor":code,"points":score}],evidence_citations=[{"citation_id":f"financial:{key}","type":"financial_authorization_packet","sha256":"a"*64}],recommendations=["Authorized human finance investigator should review the cited records."],adjudication_authority="none",accounting_authority="none",fund_movement_authority="none",payload_sha256="b"*64,created_at=__import__('datetime').datetime.now(__import__('datetime').UTC));db.add(inv);db.flush()
    svc=FinancialInvestigationService(db,"tenant-a");c=svc.create_from_anomaly(inv.investigation_id,"finance-op",idempotency_key=f"create-{key}");return svc,c

def test_anomaly_to_case_builds_immutable_evidence_pack_cluster_and_sla_task():
    f=factory()
    with f() as db:
        svc,c=seed_case(db,key="create")
        pack=svc.repo.latest_pack(c.case_id);assert pack and len(pack.payload_sha256)==64 and pack.source_watermark_sha256
        assert pack.evidence_items and c.case_type=="payment_integrity" and c.cluster_key
        assert svc.repo.tasks(c.case_id)[0].task_type=="investigation_triage"
        assert db.query(FinancialInvestigationEvidencePackModel).count()==1

def test_exclusive_human_investigator_lease_root_cause_and_ai_disagreement_capture():
    f=factory()
    with f() as db:
        svc,c=seed_case(db,code="duplicate_payment",key="lease")
        l=svc.acquire_lease(c.case_id,"finance-op",expected_case_version=1)
        assert l["case"].assigned_investigator_user_id=="finance-op" and l["lease_token"]
        with pytest.raises(ReviewConflictError):svc.classify_root_cause(c.case_id,"finance-op",root_cause_code="data_quality",rationale="Human review finds the anomaly was caused by a source-system duplication rather than an actual duplicate payment.",ai_disagreement_rationale=None,expected_case_version=2,lease_token=l["lease_token"])
        c=svc.classify_root_cause(c.case_id,"finance-op",root_cause_code="data_quality",rationale="Human review finds the anomaly was caused by a source-system duplication rather than an actual duplicate payment.",ai_disagreement_rationale="The deterministic recommendation labels the signal as duplicate payment, but the cited ledger has only one authorized payment fingerprint.",expected_case_version=2,lease_token=l["lease_token"])
        assert c.root_cause_code=="data_quality" and c.ai_disagreement_rationale
        with pytest.raises(ReviewLockError):svc.classify_root_cause(c.case_id,"finance-op",root_cause_code="data_quality",rationale="Attempt with an invalid lease token must fail closed for governed investigation mutations.",ai_disagreement_rationale=None,expected_case_version=3,lease_token="x"*32)

def test_material_remediation_requires_independent_second_human_and_creates_governed_recoupment_referral():
    f=factory()
    with f() as db:
        svc,c=seed_case(db,code="overpayment",key="remed")
        l=svc.acquire_lease(c.case_id,"finance-op",expected_case_version=1)
        c=svc.classify_root_cause(c.case_id,"finance-op",root_cause_code="overpayment",rationale="Human finance investigation confirms that the cited remittance exceeds the governed payable obligation and requires a controlled recovery referral.",ai_disagreement_rationale=None,expected_case_version=2,lease_token=l["lease_token"])
        p=svc.propose_remediation(c.case_id,"finance-op",remediation_type="recoupment_referral",amount=Decimal("250"),currency="USD",reason_code="verified_overpayment",rationale="Create a governed Release 41 recoupment request; do not post accounting or move funds from the investigation layer.",idempotency_key="remed-propose",lease_token=l["lease_token"])
        assert p.material and p.status=="pending_second_approval"
        with pytest.raises(ReviewConflictError):svc.approve_remediation(c.case_id,p.proposal_id,"finance-op",rationale="Same human cannot approve material remediation under segregation of duties.",idempotency_key="bad-approve")
        p=svc.approve_remediation(c.case_id,p.proposal_id,"finance-approver",rationale="Independent finance approver validates the evidence-bound recovery referral and amount before the investigator creates the governed accounting request.",idempotency_key="approve-remed");assert p.status=="approved"
        p=svc.execute_referral(c.case_id,p.proposal_id,"finance-op",lease_token=l["lease_token"],idempotency_key="execute-remed")
        assert p.status=="executed" and p.referral_type=="accounting_recoupment_request"
        a=db.get(AccountingAdjustmentModel,p.referral_id);assert a and a.status=="pending_approval"

def test_payment_hold_referral_uses_existing_governed_release40_hold_not_direct_payment_mutation():
    f=factory()
    with f() as db:
        svc,c=seed_case(db,code="duplicate_payment",key="hold")
        l=svc.acquire_lease(c.case_id,"finance-op",expected_case_version=1)
        svc.classify_root_cause(c.case_id,"finance-op",root_cause_code="duplicate_payment",rationale="Human investigation confirms duplicate-payment risk from the evidence pack and requires a temporary governed payment hold while correction is reviewed.",ai_disagreement_rationale=None,expected_case_version=2,lease_token=l["lease_token"])
        p=svc.propose_remediation(c.case_id,"finance-op",remediation_type="payment_hold",amount=Decimal("1000"),currency="USD",reason_code="duplicate_risk",rationale="Place a governed payment-integrity hold using the Release 40 control; this investigation service must not authorize or execute settlement.",idempotency_key="hold-prop",lease_token=l["lease_token"])
        svc.approve_remediation(c.case_id,p.proposal_id,"finance-approver",rationale="Independent finance approver authorizes only the investigation hold referral, not movement of funds.",idempotency_key="hold-second")
        p=svc.execute_referral(c.case_id,p.proposal_id,"finance-op",lease_token=l["lease_token"],idempotency_key="hold-exec")
        assert db.get(PaymentHoldModel,p.referral_id).active is True

def test_human_case_closure_blocks_pending_material_remediation_and_preserves_hash_chain():
    f=factory()
    with f() as db:
        svc,c=seed_case(db,code="returned_payment",key="close")
        l=svc.acquire_lease(c.case_id,"finance-op",expected_case_version=1)
        c=svc.classify_root_cause(c.case_id,"finance-op",root_cause_code="returned_payment",rationale="Human review confirms the external return evidence and classifies the payment integrity root cause before closure.",ai_disagreement_rationale=None,expected_case_version=2,lease_token=l["lease_token"])
        p=svc.propose_remediation(c.case_id,"finance-op",remediation_type="recoupment_referral",amount=Decimal("125"),currency="USD",reason_code="return_recovery",rationale="Material recovery referral remains pending second-human approval and therefore must block investigation closure.",idempotency_key="close-prop",lease_token=l["lease_token"])
        with pytest.raises(ReviewConflictError):svc.close_case(c.case_id,"finance-op",reason_code="remediated",rationale="Attempted closure must fail while a material remediation remains awaiting independent human approval.",expected_case_version=3,lease_token=l["lease_token"],idempotency_key="close-block")
        svc.approve_remediation(c.case_id,p.proposal_id,"finance-approver",rationale="Second human approves the evidence-bound remediation referral before closure can continue.",idempotency_key="close-approve");svc.execute_referral(c.case_id,p.proposal_id,"finance-op",lease_token=l["lease_token"],idempotency_key="close-execute")
        c=svc.close_case(c.case_id,"finance-op",reason_code="referred_for_governed_recovery",rationale="Human investigator closes the case after root cause classification and governed remediation referral are complete.",expected_case_version=3,lease_token=l["lease_token"],idempotency_key="close-final")
        assert c.status=="closed" and c.closed_at
        audit=svc.repo.audit(c.case_id);assert len(audit)>=6 and all(len(x.event_sha256)==64 for x in audit);assert all(audit[i].previous_event_sha256==audit[i-1].event_sha256 for i in range(1,len(audit)))

def test_release43_worker_and_authority_contract_fail_closed():
    from pathlib import Path
    root=Path(__file__).resolve().parents[2];domain=(root/'backend/app/domain/financial_investigation.py').read_text();worker=(root/'backend/app/workers/financial_investigation.py').read_text();migration=(root/'backend/alembic/versions/0038_financial_investigation_case_management.py').read_text()
    for token in ['"ai_can_close_case": False','"ai_can_place_payment_hold": False','"ai_can_create_accounting_adjustment": False','"ai_can_approve_remediation": False','"background_worker_can_move_funds": False','"material_remediation_dual_approval_required": True']:assert token in domain
    for forbidden in ['approve_remediation(', 'execute_referral(', 'place_hold(', 'authorize_packet(', '_post_journal(', 'close_period(', 'handoff(']:assert forbidden not in worker
    assert 'ENABLE ROW LEVEL SECURITY' in migration and 'FORCE ROW LEVEL SECURITY' in migration and 'reject_financial_investigation_immutable_mutation' in migration
