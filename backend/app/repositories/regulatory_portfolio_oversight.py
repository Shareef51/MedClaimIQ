from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import set_tenant_context
from app.models.regulatory_portfolio_oversight import *

class RegulatoryPortfolioOversightRepository:
    def __init__(self,session:Session,tenant_id:str):self.session=session;self.tenant_id=tenant_id;set_tenant_context(session,tenant_id)
    def add(self,row):
        if row.tenant_id!=self.tenant_id:raise ValueError("tenant mismatch")
        self.session.add(row);self.session.flush();return row
    def controls(self):return list(self.session.scalars(select(EnterpriseControlModel).where(EnterpriseControlModel.tenant_id==self.tenant_id).order_by(EnterpriseControlModel.control_key,EnterpriseControlModel.control_version)))
    def control(self,control_id):return self.session.scalar(select(EnterpriseControlModel).where(EnterpriseControlModel.tenant_id==self.tenant_id,EnterpriseControlModel.control_id==control_id))
    def mappings(self):return list(self.session.scalars(select(RegulatoryControlFindingMapModel).where(RegulatoryControlFindingMapModel.tenant_id==self.tenant_id)))
    def mappings_for_plan(self,plan_id):return list(self.session.scalars(select(RegulatoryControlFindingMapModel).where(RegulatoryControlFindingMapModel.tenant_id==self.tenant_id,RegulatoryControlFindingMapModel.plan_id==plan_id)))
    def snapshots(self):return list(self.session.scalars(select(RegulatoryPortfolioSnapshotModel).where(RegulatoryPortfolioSnapshotModel.tenant_id==self.tenant_id).order_by(RegulatoryPortfolioSnapshotModel.created_at.desc())))
    def snapshots_for_period(self,period_key):return list(self.session.scalars(select(RegulatoryPortfolioSnapshotModel).where(RegulatoryPortfolioSnapshotModel.tenant_id==self.tenant_id,RegulatoryPortfolioSnapshotModel.period_key==period_key).order_by(RegulatoryPortfolioSnapshotModel.snapshot_version)))
    def snapshot(self,snapshot_id):return self.session.scalar(select(RegulatoryPortfolioSnapshotModel).where(RegulatoryPortfolioSnapshotModel.tenant_id==self.tenant_id,RegulatoryPortfolioSnapshotModel.snapshot_id==snapshot_id))
    def clusters(self,snapshot_id):return list(self.session.scalars(select(RegulatorySystemicRiskClusterModel).where(RegulatorySystemicRiskClusterModel.tenant_id==self.tenant_id,RegulatorySystemicRiskClusterModel.snapshot_id==snapshot_id).order_by(RegulatorySystemicRiskClusterModel.severity.desc(),RegulatorySystemicRiskClusterModel.member_count.desc())))
    def campaign(self,campaign_id):return self.session.scalar(select(RegulatoryControlTestingCampaignModel).where(RegulatoryControlTestingCampaignModel.tenant_id==self.tenant_id,RegulatoryControlTestingCampaignModel.campaign_id==campaign_id))
    def campaigns(self,snapshot_id):return list(self.session.scalars(select(RegulatoryControlTestingCampaignModel).where(RegulatoryControlTestingCampaignModel.tenant_id==self.tenant_id,RegulatoryControlTestingCampaignModel.snapshot_id==snapshot_id).order_by(RegulatoryControlTestingCampaignModel.created_at)))
    def results(self,campaign_id):return list(self.session.scalars(select(RegulatoryControlTestingResultModel).where(RegulatoryControlTestingResultModel.tenant_id==self.tenant_id,RegulatoryControlTestingResultModel.campaign_id==campaign_id).order_by(RegulatoryControlTestingResultModel.tested_at)))
    def risk_acceptances(self,snapshot_id):return list(self.session.scalars(select(RegulatoryRiskAcceptanceModel).where(RegulatoryRiskAcceptanceModel.tenant_id==self.tenant_id,RegulatoryRiskAcceptanceModel.snapshot_id==snapshot_id)))
    def risk_acceptance(self,snapshot_id,risk_key):return self.session.scalar(select(RegulatoryRiskAcceptanceModel).where(RegulatoryRiskAcceptanceModel.tenant_id==self.tenant_id,RegulatoryRiskAcceptanceModel.snapshot_id==snapshot_id,RegulatoryRiskAcceptanceModel.risk_key==risk_key))
    def management_attestation(self,snapshot_id):return self.session.scalar(select(RegulatoryManagementAttestationModel).where(RegulatoryManagementAttestationModel.tenant_id==self.tenant_id,RegulatoryManagementAttestationModel.snapshot_id==snapshot_id))
    def certifications(self,snapshot_id):return list(self.session.scalars(select(RegulatoryPortfolioCertificationModel).where(RegulatoryPortfolioCertificationModel.tenant_id==self.tenant_id,RegulatoryPortfolioCertificationModel.snapshot_id==snapshot_id).order_by(RegulatoryPortfolioCertificationModel.certification_sequence)))
    def audit(self,snapshot_id):return list(self.session.scalars(select(RegulatoryPortfolioAuditEventModel).where(RegulatoryPortfolioAuditEventModel.tenant_id==self.tenant_id,RegulatoryPortfolioAuditEventModel.snapshot_id==snapshot_id).order_by(RegulatoryPortfolioAuditEventModel.sequence)))
