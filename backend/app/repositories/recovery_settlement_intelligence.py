from __future__ import annotations
from sqlalchemy import func,select
from sqlalchemy.orm import Session
from app.db.session import set_tenant_context
from app.models.recovery_settlement_intelligence import *

class RecoverySettlementIntelligenceRepository:
    def __init__(self,session:Session,tenant_id:str):self.session=session;self.tenant_id=tenant_id;set_tenant_context(session,tenant_id)
    def add(self,row):
        if row.tenant_id!=self.tenant_id:raise ValueError("tenant mismatch")
        self.session.add(row);self.session.flush();return row
    def statement_by_watermark(self,provider_id,watermark):return self.session.scalar(select(ProviderRecoveryBalanceStatementModel).where(ProviderRecoveryBalanceStatementModel.tenant_id==self.tenant_id,ProviderRecoveryBalanceStatementModel.provider_organization_id==provider_id,ProviderRecoveryBalanceStatementModel.source_watermark_sha256==watermark))
    def next_statement_version(self,provider_id):return int(self.session.scalar(select(func.max(ProviderRecoveryBalanceStatementModel.statement_version)).where(ProviderRecoveryBalanceStatementModel.tenant_id==self.tenant_id,ProviderRecoveryBalanceStatementModel.provider_organization_id==provider_id)) or 0)+1
    def statements(self,provider_id):return list(self.session.scalars(select(ProviderRecoveryBalanceStatementModel).where(ProviderRecoveryBalanceStatementModel.tenant_id==self.tenant_id,ProviderRecoveryBalanceStatementModel.provider_organization_id==provider_id).order_by(ProviderRecoveryBalanceStatementModel.statement_version.desc())))
    def statement(self,statement_id):return self.session.scalar(select(ProviderRecoveryBalanceStatementModel).where(ProviderRecoveryBalanceStatementModel.tenant_id==self.tenant_id,ProviderRecoveryBalanceStatementModel.statement_id==statement_id))
    def delivery(self,statement_id):return self.session.scalar(select(ProviderBalanceStatementDeliveryModel).where(ProviderBalanceStatementDeliveryModel.tenant_id==self.tenant_id,ProviderBalanceStatementDeliveryModel.statement_id==statement_id))
    def analytics_by_watermark(self,scope_type,scope_id,watermark):return self.session.scalar(select(RecoverySettlementAnalyticsSnapshotModel).where(RecoverySettlementAnalyticsSnapshotModel.tenant_id==self.tenant_id,RecoverySettlementAnalyticsSnapshotModel.scope_type==scope_type,RecoverySettlementAnalyticsSnapshotModel.scope_id==scope_id,RecoverySettlementAnalyticsSnapshotModel.source_watermark_sha256==watermark))
    def report_by_watermark(self,scope,scope_id,watermark):return self.session.scalar(select(RecoveryCloseoutReportModel).where(RecoveryCloseoutReportModel.tenant_id==self.tenant_id,RecoveryCloseoutReportModel.report_scope==scope,RecoveryCloseoutReportModel.scope_id==scope_id,RecoveryCloseoutReportModel.source_watermark_sha256==watermark))
    def next_report_version(self,scope,scope_id):return int(self.session.scalar(select(func.max(RecoveryCloseoutReportModel.report_version)).where(RecoveryCloseoutReportModel.tenant_id==self.tenant_id,RecoveryCloseoutReportModel.report_scope==scope,RecoveryCloseoutReportModel.scope_id==scope_id)) or 0)+1
