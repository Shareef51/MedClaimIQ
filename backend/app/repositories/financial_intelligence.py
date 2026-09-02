from __future__ import annotations
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import set_tenant_context
from app.models.financial_intelligence import *

class FinancialIntelligenceRepository:
    def __init__(self, session: Session, tenant_id: str):
        self.session = session; self.tenant_id = tenant_id; set_tenant_context(session, tenant_id)
    def add(self, row):
        if row.tenant_id != self.tenant_id: raise ValueError("tenant mismatch")
        self.session.add(row); self.session.flush(); return row
    def latest_reserve(self, claim_id: str):
        return self.session.scalar(select(ClaimReserveSnapshotModel).where(ClaimReserveSnapshotModel.tenant_id==self.tenant_id, ClaimReserveSnapshotModel.claim_id==claim_id).order_by(ClaimReserveSnapshotModel.created_at.desc()).limit(1))
    def reserve_by_watermark(self, claim_id: str, watermark: str):
        return self.session.scalar(select(ClaimReserveSnapshotModel).where(ClaimReserveSnapshotModel.tenant_id==self.tenant_id, ClaimReserveSnapshotModel.claim_id==claim_id, ClaimReserveSnapshotModel.source_watermark_sha256==watermark))
    def analytics_by_watermark(self, scope_type: str, scope_id: str, watermark: str):
        return self.session.scalar(select(FinancialAnalyticsSnapshotModel).where(FinancialAnalyticsSnapshotModel.tenant_id==self.tenant_id, FinancialAnalyticsSnapshotModel.scope_type==scope_type, FinancialAnalyticsSnapshotModel.scope_id==scope_id, FinancialAnalyticsSnapshotModel.source_watermark_sha256==watermark))
    def reserve_history(self, claim_id: str):
        return list(self.session.scalars(select(ClaimReserveSnapshotModel).where(ClaimReserveSnapshotModel.tenant_id==self.tenant_id, ClaimReserveSnapshotModel.claim_id==claim_id).order_by(ClaimReserveSnapshotModel.created_at)))
    def investigations(self, claim_id: str | None = None):
        q=select(FinancialAnomalyInvestigationModel).where(FinancialAnomalyInvestigationModel.tenant_id==self.tenant_id)
        if claim_id: q=q.where(FinancialAnomalyInvestigationModel.claim_id==claim_id)
        return list(self.session.scalars(q.order_by(FinancialAnomalyInvestigationModel.created_at.desc())))
