from __future__ import annotations
from datetime import UTC,datetime,timedelta
from decimal import Decimal
import pytest
from sqlalchemy import select
from app.models.tenancy import UserAccountModel,TenantMembershipModel
from app.services.financial_handoff import FinancialHandoffService
from app.services.accounting_ledger import AccountingLedgerService
from app.models.accounting_ledger import AccountingPeriodModel,LedgerJournalModel
from app.services.review_workbench import ReviewConflictError
from tests.test_financial_handoff import setup_finance,close_original
from tests.test_appeal_evidence_reconsideration import factory

def setup_accounting(db):
    db.add(UserAccountModel(user_id="acct-controller",external_issuer="https://id.example",external_subject="acct-controller",display_name="Accounting Controller",status="active"));db.flush()
    db.add(TenantMembershipModel(membership_id="m-acct-controller",tenant_id="tenant-a",user_id="acct-controller",role="accounting_controller",status="active"));db.flush()

def paid_intent(db,key="acct"):
    setup_finance(db);setup_accounting(db);close_original(db);f=FinancialHandoffService(db,"tenant-a")
    p=f.prepare_packet("claim-1","finance-op",idempotency_key=f"{key}-packet");f.lock_packet("claim-1",p.packet_id,"finance-op",expected_packet_version=1,idempotency_key=f"{key}-lock");f.authorize_packet("claim-1",p.packet_id,"finance-approver",rationale="Independent human finance approver validates the immutable financial packet before accounting integration.",idempotency_key=f"{key}-auth")
    i=f.stage_payment_intent("claim-1",p.packet_id,"finance-op",payee_ref="provider:org-a",idempotency_key=f"{key}-intent");f.handoff("claim-1",i.payment_intent_id,actor_id="finance-op",idempotency_key=f"{key}-handoff");db.flush();return i

def test_multi_part_era_eft_reconciles_and_posts_balanced_immutable_journal():
    f=factory()
    with f() as db:
        i=paid_intent(db,"multi");svc=AccountingLedgerService(db,"tenant-a")
        svc.record_era("claim-1",i.payment_intent_id,"finance-op",era_reference="ERA-1",payment_reference="BATCH-99",provider_ref="provider:org-a",paid_amount=Decimal("400"))
        svc.record_era("claim-1",i.payment_intent_id,"finance-op",era_reference="ERA-2",payment_reference="BATCH-99",provider_ref="provider:org-a",paid_amount=Decimal("600"))
        svc.record_eft("claim-1",i.payment_intent_id,"finance-op",eft_reference="EFT-1",bank_reference="BATCH-99",trace_number="TRACE-1",amount=Decimal("250"))
        r=svc.reconcile("claim-1",i.payment_intent_id,"finance-op",idempotency_key="multi-recon-partial");assert r.status=="partial" and r.matched_amount==Decimal("250.00")
        svc.record_eft("claim-1",i.payment_intent_id,"finance-op",eft_reference="EFT-2",bank_reference="BATCH-99",trace_number="TRACE-2",amount=Decimal("750"))
        r=svc.reconcile("claim-1",i.payment_intent_id,"finance-op",idempotency_key="multi-recon-final");assert r.status=="reconciled" and r.journal_id
        j=db.get(LedgerJournalModel,r.journal_id);assert j.total_debits==j.total_credits==Decimal("1000.00") and len(j.journal_sha256)==64
        entries=svc.repo.entries(j.journal_id);assert {e.direction for e in entries}=={"debit","credit"}
        status=svc.repo.remittance_status(i.payment_intent_id);assert status.status=="reconciled" and status.remitted_amount==Decimal("1000.00")

def test_reference_mismatch_creates_exception_and_aging_queue():
    f=factory()
    with f() as db:
        i=paid_intent(db,"mismatch");i.created_at=datetime.now(UTC)-timedelta(days=35);svc=AccountingLedgerService(db,"tenant-a")
        svc.record_era("claim-1",i.payment_intent_id,"finance-op",era_reference="ERA-X",payment_reference="ERA-REF",provider_ref="provider:org-a",paid_amount=Decimal("1000"))
        svc.record_eft("claim-1",i.payment_intent_id,"finance-op",eft_reference="EFT-X",bank_reference="OTHER-REF",trace_number="TRACE-X",amount=Decimal("1000"))
        r=svc.reconcile("claim-1",i.payment_intent_id,"finance-op",idempotency_key="mismatch-recon");assert r.status=="exception" and not r.reference_match
        q=svc.refresh_aging_queue("finance-op");item=[x for x in q if x.payment_intent_id==i.payment_intent_id][0];assert item.aging_bucket=="31+d" and item.priority>=80

def test_returned_payment_posts_reversing_double_entry_and_provider_status():
    f=factory()
    with f() as db:
        i=paid_intent(db,"return");svc=AccountingLedgerService(db,"tenant-a")
        row=svc.record_return("claim-1",i.payment_intent_id,"finance-op",return_reference="RET-1",return_code="R01",amount=Decimal("1000"),reason="External bank reports the EFT was returned and requires accounting reversal and human operational follow-up.")
        assert row.status=="journaled" and row.journal_id
        j=db.get(LedgerJournalModel,row.journal_id);assert j.journal_type=="returned_payment_reversal" and j.total_debits==j.total_credits
        assert svc.repo.remittance_status(i.payment_intent_id).status=="returned"

def test_adjustment_and_recoupment_require_separate_human_finance_approval():
    f=factory()
    with f() as db:
        i=paid_intent(db,"adjust");svc=AccountingLedgerService(db,"tenant-a")
        a=svc.request_adjustment("claim-1",i.payment_intent_id,"finance-op",adjustment_type="recoupment",amount=Decimal("125"),reason_code="provider_overpayment",rationale="A provider overpayment was verified from reconciled remittance and requires governed recoupment accounting.",idempotency_key="recoup-request")
        with pytest.raises(ReviewConflictError):svc.approve_adjustment("claim-1",a.adjustment_id,"finance-op",rationale="Same person cannot approve their own accounting adjustment under segregation of duties.",idempotency_key="recoup-bad")
        a=svc.approve_adjustment("claim-1",a.adjustment_id,"finance-approver",rationale="Independent human finance approver confirms the recoupment basis, amount and accounting treatment.",idempotency_key="recoup-approve");assert a.status=="posted" and a.journal_id

def test_period_close_requires_accounting_controller_and_no_blocking_reconciliation():
    f=factory()
    with f() as db:
        i=paid_intent(db,"close");svc=AccountingLedgerService(db,"tenant-a")
        svc.record_era("claim-1",i.payment_intent_id,"finance-op",era_reference="ERA-C",payment_reference="REF-C",provider_ref="provider:org-a",paid_amount=Decimal("1000"));svc.record_eft("claim-1",i.payment_intent_id,"finance-op",eft_reference="EFT-C",bank_reference="REF-C",trace_number="TRACE-C",amount=Decimal("1000"));svc.reconcile("claim-1",i.payment_intent_id,"finance-op",idempotency_key="close-recon")
        p=db.scalar(select(AccountingPeriodModel));assert p.status=="open"
        with pytest.raises(ReviewConflictError):svc.close_period(p.period_id,"finance-approver",expected_lock_version=1,rationale="Only an accounting controller can close a balanced accounting period after reconciliation is complete.",idempotency_key="close-bad")
        p=svc.close_period(p.period_id,"acct-controller",expected_lock_version=1,rationale="Accounting controller confirms balanced journals, reconciled payments, no pending adjustments and closes the period.",idempotency_key="close-good");assert p.status=="closed" and p.close_sha256 and p.closed_by_user_id=="acct-controller"

def test_release41_authority_and_migration_contract_fail_closed():
    from pathlib import Path
    root=Path(__file__).resolve().parents[2];domain=(root/'backend/app/domain/accounting_ledger.py').read_text();migration=(root/'backend/alembic/versions/0036_accounting_ledger_era_eft_close.py').read_text();service=(root/'backend/app/services/accounting_ledger.py').read_text()
    for token in ['"llm_can_post_journal":False','"background_worker_can_close_period":False','"automatic_fund_movement":False']:assert token in domain
    assert 'ENABLE ROW LEVEL SECURITY' in migration and 'FORCE ROW LEVEL SECURITY' in migration and 'reject_immutable_ledger_journal_mutation' in migration and 'reject_closed_accounting_period_mutation' in migration
    assert 'double-entry journal must be non-zero and exactly balanced' in service and 'human accounting controller membership required' in service
