from __future__ import annotations
from sqlalchemy import func,select
from sqlalchemy.orm import Session
from app.db.session import set_tenant_context
from app.models.provider_dispute_intelligence import *

class ProviderDisputeIntelligenceRepository:
    def __init__(self,session:Session,tenant_id:str):self.session=session;self.tenant_id=tenant_id;set_tenant_context(session,tenant_id)
    def add(self,row):self.session.add(row);self.session.flush();return row
    def reingestion(self,dispute_id,source_kind,source_id,source_version):return self.session.scalar(select(DisputeEvidenceReingestionModel).where(DisputeEvidenceReingestionModel.tenant_id==self.tenant_id,DisputeEvidenceReingestionModel.dispute_id==dispute_id,DisputeEvidenceReingestionModel.source_kind==source_kind,DisputeEvidenceReingestionModel.source_id==source_id,DisputeEvidenceReingestionModel.source_version==source_version))
    def reingestions(self,dispute_id):return list(self.session.scalars(select(DisputeEvidenceReingestionModel).where(DisputeEvidenceReingestionModel.tenant_id==self.tenant_id,DisputeEvidenceReingestionModel.dispute_id==dispute_id).order_by(DisputeEvidenceReingestionModel.started_at)))
    def snapshots(self,dispute_id):return list(self.session.scalars(select(DisputeEvidenceSnapshotModel).where(DisputeEvidenceSnapshotModel.tenant_id==self.tenant_id,DisputeEvidenceSnapshotModel.dispute_id==dispute_id).order_by(DisputeEvidenceSnapshotModel.snapshot_version)))
    def latest_snapshot(self,dispute_id):return self.session.scalar(select(DisputeEvidenceSnapshotModel).where(DisputeEvidenceSnapshotModel.tenant_id==self.tenant_id,DisputeEvidenceSnapshotModel.dispute_id==dispute_id).order_by(DisputeEvidenceSnapshotModel.snapshot_version.desc()).limit(1))
    def next_snapshot_version(self,dispute_id):return int(self.session.scalar(select(func.max(DisputeEvidenceSnapshotModel.snapshot_version)).where(DisputeEvidenceSnapshotModel.tenant_id==self.tenant_id,DisputeEvidenceSnapshotModel.dispute_id==dispute_id)) or 0)+1
    def agreements(self,provider_org):return list(self.session.scalars(select(ProviderAgreementVersionModel).where(ProviderAgreementVersionModel.tenant_id==self.tenant_id,ProviderAgreementVersionModel.provider_organization_id==provider_org,ProviderAgreementVersionModel.status=="approved").order_by(ProviderAgreementVersionModel.effective_from.desc())))
    def policies(self):return list(self.session.scalars(select(ReimbursementPolicyVersionModel).where(ReimbursementPolicyVersionModel.tenant_id==self.tenant_id,ReimbursementPolicyVersionModel.status=="approved").order_by(ReimbursementPolicyVersionModel.effective_from.desc())))
    def comparisons(self,dispute_id):return list(self.session.scalars(select(DisputeEvidenceComparisonModel).where(DisputeEvidenceComparisonModel.tenant_id==self.tenant_id,DisputeEvidenceComparisonModel.dispute_id==dispute_id).order_by(DisputeEvidenceComparisonModel.created_at)))
    def rag_runs(self,dispute_id):return list(self.session.scalars(select(DisputeRAGRunModel).where(DisputeRAGRunModel.tenant_id==self.tenant_id,DisputeRAGRunModel.dispute_id==dispute_id).order_by(DisputeRAGRunModel.created_at)))
    def rag_items(self,run_id):return list(self.session.scalars(select(DisputeRAGItemModel).where(DisputeRAGItemModel.tenant_id==self.tenant_id,DisputeRAGItemModel.run_id==run_id).order_by(DisputeRAGItemModel.rank)))
    def recommendation_runs(self,dispute_id):return list(self.session.scalars(select(DisputeRecommendationRunModel).where(DisputeRecommendationRunModel.tenant_id==self.tenant_id,DisputeRecommendationRunModel.dispute_id==dispute_id).order_by(DisputeRecommendationRunModel.created_at)))
    def checkpoints(self,dispute_id):return list(self.session.scalars(select(DisputeReviewCheckpointModel).where(DisputeReviewCheckpointModel.tenant_id==self.tenant_id,DisputeReviewCheckpointModel.dispute_id==dispute_id).order_by(DisputeReviewCheckpointModel.created_at)))
    def next_checkpoint_version(self,thread_id):return int(self.session.scalar(select(func.max(DisputeReviewCheckpointModel.checkpoint_version)).where(DisputeReviewCheckpointModel.tenant_id==self.tenant_id,DisputeReviewCheckpointModel.thread_id==thread_id)) or 0)+1
    def missing_requests(self,dispute_id):return list(self.session.scalars(select(DisputeMissingEvidenceRequestModel).where(DisputeMissingEvidenceRequestModel.tenant_id==self.tenant_id,DisputeMissingEvidenceRequestModel.dispute_id==dispute_id).order_by(DisputeMissingEvidenceRequestModel.created_at)))
    def responses(self,dispute_id):return list(self.session.scalars(select(ProviderDisputeResponseModel).where(ProviderDisputeResponseModel.tenant_id==self.tenant_id,ProviderDisputeResponseModel.dispute_id==dispute_id).order_by(ProviderDisputeResponseModel.created_at)))
