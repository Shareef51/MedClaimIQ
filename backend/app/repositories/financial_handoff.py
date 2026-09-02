from __future__ import annotations
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.db.session import set_tenant_context
from app.models.financial_handoff import *

class FinancialHandoffRepository:
    def __init__(self,session:Session,tenant_id:str): self.session=session; self.tenant_id=tenant_id; set_tenant_context(session,tenant_id)
    def add(self,row):
        if row.tenant_id!=self.tenant_id: raise ValueError("tenant mismatch")
        self.session.add(row); self.session.flush(); return row
    def packet(self,packet_id,for_update=False):
        q=select(FinancialAuthorizationPacketModel).where(FinancialAuthorizationPacketModel.tenant_id==self.tenant_id,FinancialAuthorizationPacketModel.packet_id==packet_id)
        if for_update:q=q.with_for_update()
        return self.session.scalar(q)
    def latest_packet(self,claim_id): return self.session.scalar(select(FinancialAuthorizationPacketModel).where(FinancialAuthorizationPacketModel.tenant_id==self.tenant_id,FinancialAuthorizationPacketModel.claim_id==claim_id).order_by(FinancialAuthorizationPacketModel.packet_version.desc()).limit(1))
    def artifacts(self,packet_id): return list(self.session.scalars(select(RemittanceArtifactModel).where(RemittanceArtifactModel.tenant_id==self.tenant_id,RemittanceArtifactModel.packet_id==packet_id)))
    def active_holds(self,claim_id): return list(self.session.scalars(select(PaymentHoldModel).where(PaymentHoldModel.tenant_id==self.tenant_id,PaymentHoldModel.claim_id==claim_id,PaymentHoldModel.active.is_(True))))
    def intent(self,payment_intent_id,for_update=False):
        q=select(PaymentIntentModel).where(PaymentIntentModel.tenant_id==self.tenant_id,PaymentIntentModel.payment_intent_id==payment_intent_id)
        if for_update:q=q.with_for_update()
        return self.session.scalar(q)
    def intent_for_packet(self,packet_id): return self.session.scalar(select(PaymentIntentModel).where(PaymentIntentModel.tenant_id==self.tenant_id,PaymentIntentModel.packet_id==packet_id))
    def intents(self,claim_id): return list(self.session.scalars(select(PaymentIntentModel).where(PaymentIntentModel.tenant_id==self.tenant_id,PaymentIntentModel.claim_id==claim_id).order_by(PaymentIntentModel.created_at)))
    def handoffs(self,payment_intent_id): return list(self.session.scalars(select(FinancialHandoffModel).where(FinancialHandoffModel.tenant_id==self.tenant_id,FinancialHandoffModel.payment_intent_id==payment_intent_id).order_by(FinancialHandoffModel.created_at)))
    def settlement_by_provider_event(self,event_id): return self.session.scalar(select(SettlementEventModel).where(SettlementEventModel.tenant_id==self.tenant_id,SettlementEventModel.provider_event_id==event_id))
    def settlements(self,payment_intent_id): return list(self.session.scalars(select(SettlementEventModel).where(SettlementEventModel.tenant_id==self.tenant_id,SettlementEventModel.payment_intent_id==payment_intent_id).order_by(SettlementEventModel.occurred_at)))
    def exceptions(self,claim_id): return list(self.session.scalars(select(FinancialReconciliationExceptionModel).where(FinancialReconciliationExceptionModel.tenant_id==self.tenant_id,FinancialReconciliationExceptionModel.claim_id==claim_id).order_by(FinancialReconciliationExceptionModel.created_at)))
    def audit(self,claim_id): return list(self.session.scalars(select(FinancialAuditEventModel).where(FinancialAuditEventModel.tenant_id==self.tenant_id,FinancialAuditEventModel.claim_id==claim_id).order_by(FinancialAuditEventModel.sequence)))
    def next_audit_sequence(self,claim_id): return int(self.session.scalar(select(func.max(FinancialAuditEventModel.sequence)).where(FinancialAuditEventModel.tenant_id==self.tenant_id,FinancialAuditEventModel.claim_id==claim_id)) or 0)+1
    def tasks(self,claim_id): return list(self.session.scalars(select(FinancialTaskModel).where(FinancialTaskModel.tenant_id==self.tenant_id,FinancialTaskModel.claim_id==claim_id).order_by(FinancialTaskModel.created_at)))
