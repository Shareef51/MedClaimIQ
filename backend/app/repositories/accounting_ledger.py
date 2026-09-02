from __future__ import annotations
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import set_tenant_context
from app.models.accounting_ledger import *

class AccountingLedgerRepository:
    def __init__(self,session:Session,tenant_id:str):self.session=session;self.tenant_id=tenant_id;set_tenant_context(session,tenant_id)
    def add(self,row):
        if row.tenant_id!=self.tenant_id:raise ValueError("tenant mismatch")
        self.session.add(row);self.session.flush();return row
    def period(self,period_id):return self.session.scalar(select(AccountingPeriodModel).where(AccountingPeriodModel.tenant_id==self.tenant_id,AccountingPeriodModel.period_id==period_id))
    def period_by_key(self,key):return self.session.scalar(select(AccountingPeriodModel).where(AccountingPeriodModel.tenant_id==self.tenant_id,AccountingPeriodModel.period_key==key))
    def journals(self,claim_id=None):
        q=select(LedgerJournalModel).where(LedgerJournalModel.tenant_id==self.tenant_id)
        if claim_id:q=q.where(LedgerJournalModel.claim_id==claim_id)
        return list(self.session.scalars(q.order_by(LedgerJournalModel.created_at,LedgerJournalModel.journal_id)))
    def entries(self,journal_id):return list(self.session.scalars(select(LedgerEntryModel).where(LedgerEntryModel.tenant_id==self.tenant_id,LedgerEntryModel.journal_id==journal_id).order_by(LedgerEntryModel.entry_sequence)))
    def eras(self,intent_id):return list(self.session.scalars(select(ERARecordModel).where(ERARecordModel.tenant_id==self.tenant_id,ERARecordModel.payment_intent_id==intent_id).order_by(ERARecordModel.received_at)))
    def efts(self,intent_id):return list(self.session.scalars(select(EFTRecordModel).where(EFTRecordModel.tenant_id==self.tenant_id,EFTRecordModel.payment_intent_id==intent_id).order_by(EFTRecordModel.received_at)))
    def reconciliation(self,intent_id):return self.session.scalar(select(PaymentReconciliationModel).where(PaymentReconciliationModel.tenant_id==self.tenant_id,PaymentReconciliationModel.payment_intent_id==intent_id))
    def returns(self,intent_id):return list(self.session.scalars(select(ReturnedPaymentModel).where(ReturnedPaymentModel.tenant_id==self.tenant_id,ReturnedPaymentModel.payment_intent_id==intent_id).order_by(ReturnedPaymentModel.received_at)))
    def adjustments(self,claim_id):return list(self.session.scalars(select(AccountingAdjustmentModel).where(AccountingAdjustmentModel.tenant_id==self.tenant_id,AccountingAdjustmentModel.claim_id==claim_id).order_by(AccountingAdjustmentModel.created_at)))
    def remittance_status(self,intent_id):return self.session.scalar(select(ProviderRemittanceStatusModel).where(ProviderRemittanceStatusModel.tenant_id==self.tenant_id,ProviderRemittanceStatusModel.payment_intent_id==intent_id))
    def queue(self,claim_id=None):
        q=select(AccountingReconciliationQueueModel).where(AccountingReconciliationQueueModel.tenant_id==self.tenant_id)
        if claim_id:q=q.where(AccountingReconciliationQueueModel.claim_id==claim_id)
        return list(self.session.scalars(q.order_by(AccountingReconciliationQueueModel.priority.desc(),AccountingReconciliationQueueModel.age_days.desc())))
