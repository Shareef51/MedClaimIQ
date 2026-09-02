from __future__ import annotations
from decimal import Decimal
from pathlib import Path
import pytest
from app.models.accounting_ledger import LedgerJournalModel
from app.services.accounting_ledger import AccountingLedgerService
from app.services.provider_dispute_resolution import ProviderDisputeResolutionService
from app.services.recovery_settlement import RecoverySettlementService
from app.services.review_workbench import ReviewConflictError
from tests.test_appeal_evidence_reconsideration import factory
from tests.test_provider_dispute_resolution import prepare_intelligence

def release46_final(db,key="p47",target=Decimal("100")):
    recovery,c,d,intel,material,citations,cps=prepare_intelligence(db,key);p46=ProviderDisputeResolutionService(db,"tenant-a");c=recovery.repo.case(c.recovery_case_id)
    p=p46.save_packet(c.recovery_case_id,d.dispute_id,"finance-approver",outcome="reduce_recovery",amended_target_amount=target,rationale="Independent human finance approver resolves the evidence-bound provider dispute and establishes the controlling recovery target before downstream settlement verification.",reason_codes=["provider_evidence_validated"],citation_refs=citations,resolved_comparison_refs=material,checkpoint_refs=cps,recommendation_disagreement_reason="The human reviewer documents independent judgment relative to the recommendation-only analysis before the recovery target is changed.",expected_case_version=c.case_version,expected_packet_version=None,idempotency_key=f"{key}-packet")
    p=p46.lock_packet(c.recovery_case_id,d.dispute_id,p.packet_id,"finance-approver",expected_packet_version=1,idempotency_key=f"{key}-lock")
    p46.second_review(c.recovery_case_id,d.dispute_id,p.packet_id,"finance-approver-2",action="approve",rationale="Second independent human finance approver confirms the locked material recovery amendment and its evidence citations.",expected_packet_version=1,idempotency_key=f"{key}-second")
    final=p46.close(c.recovery_case_id,d.dispute_id,p.packet_id,"finance-approver",expected_packet_version=1,expected_case_version=c.case_version,idempotency_key=f"{key}-close")
    db.flush();return recovery,c,d,final

def settlement_journal(db,amount=Decimal("100"),key="p47-journal"):
    svc=AccountingLedgerService(db,"tenant-a")
    return svc._post_journal(claim_id="claim-1",payment_intent_id=None,journal_type="provider_repayment_verification",source_type="external_provider_repayment_evidence",source_id=key,currency="USD",entries=[("debit","cash_clearing",amount,"Externally verified provider repayment evidence."),("credit","provider_recoupment_receivable",amount,"Reduce recovery receivable only through governed accounting evidence.")],actor_type="human_finance_approver",actor_id="finance-approver",idempotency_key=key,trace_id=None)

def test_release46_controlling_position_creates_bound_settlement_case_and_sla():
    f=factory()
    with f() as db:
        _,c,_,final=release46_final(db,"create47");svc=RecoverySettlementService(db,"tenant-a");row=svc.create_from_recovery(c.recovery_case_id,"finance-op",idempotency_key="create-settlement")
        assert row.final_resolution_id==final.resolution_id and row.target_amount==Decimal("100.00") and len(row.position_payload_sha256)==64
        assert row.remaining_amount==Decimal("100.00") and row.status=="awaiting_settlement_evidence" and {x.task_type for x in svc.repo.tasks(row.settlement_case_id)}=={"settlement_evidence_due","financial_closeout"}

def test_provider_multi_installment_evidence_requires_human_reference_verification_and_matches_exact_target():
    f=factory()
    with f() as db:
        _,c,_,_=release46_final(db,"multi47");svc=RecoverySettlementService(db,"tenant-a");s=svc.create_from_recovery(c.recovery_case_id,"finance-op",idempotency_key="multi-case")
        e1=svc.submit_evidence(s.settlement_case_id,"provider-user",evidence_type="bank_repayment",amount=Decimal("40"),currency="USD",installment_sequence=1,external_reference="BANK-P47-1",bank_reference="BANK-P47-1",remittance_reference=None,provider_reference="org-a",evidence_refs=["receipt-1"],occurred_at=None,idempotency_key="multi-e1")
        e2=svc.submit_evidence(s.settlement_case_id,"provider-user",evidence_type="bank_repayment",amount=Decimal("60"),currency="USD",installment_sequence=2,external_reference="BANK-P47-2",bank_reference="BANK-P47-2",remittance_reference=None,provider_reference="org-a",evidence_refs=["receipt-2"],occurred_at=None,idempotency_key="multi-e2")
        assert e1.status==e2.status=="pending_verification" and svc.repo.case(s.settlement_case_id).verified_amount==0
        svc.verify_evidence(s.settlement_case_id,e1.settlement_evidence_id,"finance-op",reference_match=True,verification_rationale="Human finance operator verifies the bank reference, provider relationship, amount and currency against the external repayment evidence.",expected_case_version=3,idempotency_key="multi-v1")
        svc.verify_evidence(s.settlement_case_id,e2.settlement_evidence_id,"finance-op",reference_match=True,verification_rationale="Human finance operator independently verifies the second bank installment reference, amount and currency before matching it to recovery.",expected_case_version=4,idempotency_key="multi-v2")
        current=svc.repo.case(s.settlement_case_id);assert current.verified_amount==Decimal("100.00") and current.remaining_amount==0 and current.status=="matched"

def test_reference_mismatch_creates_exception_and_does_not_count_as_recovery():
    f=factory()
    with f() as db:
        _,c,_,_=release46_final(db,"mismatch47");svc=RecoverySettlementService(db,"tenant-a");s=svc.create_from_recovery(c.recovery_case_id,"finance-op",idempotency_key="mismatch-case")
        e=svc.submit_evidence(s.settlement_case_id,"provider-user",evidence_type="provider_remittance",amount=Decimal("100"),currency="USD",installment_sequence=1,external_reference="REM-47-X",bank_reference=None,remittance_reference=None,provider_reference="org-a",evidence_refs=[],occurred_at=None,idempotency_key="mismatch-e")
        e=svc.verify_evidence(s.settlement_case_id,e.settlement_evidence_id,"finance-op",reference_match=True,verification_rationale="Human verifier cannot validate a missing remittance reference and therefore rejects the evidence from financial closeout matching.",expected_case_version=2,idempotency_key="mismatch-v")
        assert e.status=="rejected" and svc.repo.case(s.settlement_case_id).verified_amount==0
        assert any(x.exception_code=="reference_mismatch" and x.status=="open" for x in svc.repo.exceptions(s.settlement_case_id))

def test_partial_settlement_blocks_closeout_until_exact_ledger_correlation_and_independent_approval():
    f=factory()
    with f() as db:
        _,c,_,_=release46_final(db,"close47");svc=RecoverySettlementService(db,"tenant-a");s=svc.create_from_recovery(c.recovery_case_id,"finance-op",idempotency_key="close-case")
        e1=svc.submit_evidence(s.settlement_case_id,"provider-user",evidence_type="bank_repayment",amount=Decimal("40"),currency="USD",installment_sequence=1,external_reference="CLOSE-47-1",bank_reference="CLOSE-47-1",remittance_reference=None,provider_reference="org-a",evidence_refs=[],occurred_at=None,idempotency_key="close-e1")
        svc.verify_evidence(s.settlement_case_id,e1.settlement_evidence_id,"finance-op",reference_match=True,verification_rationale="Human finance operator verifies the first partial provider repayment installment.",expected_case_version=2,idempotency_key="close-v1")
        with pytest.raises(ReviewConflictError,match="unresolved recovery balance"):svc.prepare_certificate(s.settlement_case_id,"finance-op",accounting_period_id="missing",reason_codes=["external_repayment_verified"],rationale="Financial closeout must remain blocked while a recovery balance remains unresolved.",expected_case_version=3,idempotency_key="close-too-early")
        e2=svc.submit_evidence(s.settlement_case_id,"provider-user",evidence_type="recoupment_offset",amount=Decimal("60"),currency="USD",installment_sequence=2,external_reference="OFFSET-47-2",bank_reference=None,remittance_reference="ERA-OFFSET-47",provider_reference="org-a",evidence_refs=[],occurred_at=None,idempotency_key="close-e2")
        svc.verify_evidence(s.settlement_case_id,e2.settlement_evidence_id,"finance-op",reference_match=True,verification_rationale="Human finance operator verifies the governed recoupment offset reference and amount as external settlement evidence.",expected_case_version=4,idempotency_key="close-v2")
        j=settlement_journal(db);svc.correlate_ledger(s.settlement_case_id,e1.settlement_evidence_id,"finance-op",journal_id=j.journal_id,amount=Decimal("40"),currency="USD",idempotency_key="close-l1");svc.correlate_ledger(s.settlement_case_id,e2.settlement_evidence_id,"finance-op",journal_id=j.journal_id,amount=Decimal("60"),currency="USD",idempotency_key="close-l2")
        current=svc.repo.case(s.settlement_case_id);cert=svc.prepare_certificate(s.settlement_case_id,"finance-op",accounting_period_id=j.period_id,reason_codes=["external_repayment_verified","ledger_reconciled"],rationale="Human finance operator confirms the full recovery target is matched to verified provider repayment evidence and immutable ledger accounting.",expected_case_version=current.case_version,idempotency_key="close-cert")
        current=svc.repo.case(s.settlement_case_id)
        with pytest.raises(ReviewConflictError,match="approver must differ"):svc.decide_certificate(s.settlement_case_id,cert.certificate_id,"finance-op",action="approve",rationale="The same person may not certify their own financial closeout preparation.",expected_case_version=current.case_version,idempotency_key="close-self")
        cert=svc.decide_certificate(s.settlement_case_id,cert.certificate_id,"finance-approver-2",action="approve",rationale="Independent human finance approver confirms exact repayment matching, ledger correlation, accounting period linkage and zero unresolved balance.",expected_case_version=current.case_version,idempotency_key="close-approve")
        assert cert.status=="certified" and svc.repo.case(s.settlement_case_id).status=="certified" and cert.approved_by_user_id=="finance-approver-2"

def test_recovery_settlement_correspondence_traceability_and_hash_chained_audit():
    f=factory()
    with f() as db:
        _,c,_,_=release46_final(db,"trace47");svc=RecoverySettlementService(db,"tenant-a");s=svc.create_from_recovery(c.recovery_case_id,"finance-op",idempotency_key="trace-case")
        corr=svc.add_correspondence(s.settlement_case_id,"provider-user",direction="inbound",channel="portal",subject="Provider repayment reference",body="Provider supplies an external repayment reference for human finance verification without initiating any fund transfer in MedClaimIQ.",external_message_id="P47-MSG-1",idempotency_key="trace-corr")
        trace=svc.traceability(s.settlement_case_id,"finance-op");assert corr.body_sha256 and trace["controlling_position"]["position_payload_sha256"]==s.position_payload_sha256
        audit=svc.repo.audit(s.settlement_case_id);assert len(audit)>=2 and all(len(x.event_sha256)==64 for x in audit);assert all(audit[i].previous_event_sha256==audit[i-1].event_sha256 for i in range(1,len(audit)))
        assert trace["authority"]["automation_collects_funds"] is False and trace["authority"]["automation_closes_financial_recovery"] is False

def test_release47_worker_authority_migration_and_ui_contracts_fail_closed():
    root=Path(__file__).resolve().parents[2];domain=(root/'backend/app/domain/recovery_settlement.py').read_text();service=(root/'backend/app/services/recovery_settlement.py').read_text();worker=(root/'backend/app/workers/recovery_settlement.py').read_text();migration=(root/'backend/alembic/versions/0042_recovery_settlement_financial_closeout.py').read_text();ui=(root/'frontend/app/review/recovery-settlements/page.tsx').read_text();bff=(root/'frontend/app/api/reviewer/[...path]/route.ts').read_text();portal=(root/'frontend/app/api/portal/[...path]/route.ts').read_text()
    for token in ['"ai_can_collect_funds":False','"background_worker_can_create_bank_transaction":False','"background_worker_can_approve_accounting":False','"background_worker_can_authorize_payment":False','"background_worker_can_close_financial_recovery":False']:assert token in domain
    for forbidden in ['verify_evidence(', 'correlate_ledger(', 'decide_certificate(', '_post_journal(', 'authorize_packet(', 'handoff(', 'collect_funds(', 'move_money(']:assert forbidden not in worker
    assert 'down_revision="0041_provider_dispute_resolution_recovery_amendment"' in migration and 'FORCE ROW LEVEL SECURITY' in migration and 'reject_recovery_settlement_immutable_mutation' in migration
    assert 'recovery-settlements' in bff and 'portal\\/recovery-settlements' in portal and 'Independent human closeout' in ui
    assert '_post_journal(' not in service and 'collect_funds(' not in service and 'move_money(' not in service
