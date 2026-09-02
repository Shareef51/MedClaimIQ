from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import set_tenant_context
from app.models.appeal_reconsideration import (
    AppealEvidenceSnapshotModel, AppealEvidenceReingestionModel, AppealEvidenceComparisonModel,
    AppealRAGRunModel, AppealRAGItemModel, AppealReconsiderationRunModel,
    AppealReconsiderationCheckpointModel, AppealReviewerAnnotationModel,
    AppealMissingEvidenceRequestModel, AppealEscalationModel,
)


class AppealReconsiderationRepository:
    def __init__(self, session: Session, tenant_id: str) -> None:
        self.session=session; self.tenant_id=tenant_id; set_tenant_context(session,tenant_id)

    def add(self,row):
        if row.tenant_id!=self.tenant_id: raise PermissionError("cross-tenant appeal reconsideration persistence denied")
        self.session.add(row); self.session.flush(); return row

    def snapshots(self,appeal_id:str):
        return list(self.session.scalars(select(AppealEvidenceSnapshotModel).where(AppealEvidenceSnapshotModel.tenant_id==self.tenant_id,AppealEvidenceSnapshotModel.appeal_id==appeal_id).order_by(AppealEvidenceSnapshotModel.snapshot_version)))

    def latest_snapshot(self,appeal_id:str):
        return self.session.scalar(select(AppealEvidenceSnapshotModel).where(AppealEvidenceSnapshotModel.tenant_id==self.tenant_id,AppealEvidenceSnapshotModel.appeal_id==appeal_id).order_by(AppealEvidenceSnapshotModel.snapshot_version.desc()).limit(1))

    def next_snapshot_version(self,appeal_id:str)->int:
        n=self.session.scalar(select(func.max(AppealEvidenceSnapshotModel.snapshot_version)).where(AppealEvidenceSnapshotModel.tenant_id==self.tenant_id,AppealEvidenceSnapshotModel.appeal_id==appeal_id))
        return int(n or 0)+1

    def reingestions(self,appeal_id:str):
        return list(self.session.scalars(select(AppealEvidenceReingestionModel).where(AppealEvidenceReingestionModel.tenant_id==self.tenant_id,AppealEvidenceReingestionModel.appeal_id==appeal_id).order_by(AppealEvidenceReingestionModel.started_at)))

    def reingestion(self,appeal_id:str,source_kind:str,source_id:str,source_version:str):
        return self.session.scalar(select(AppealEvidenceReingestionModel).where(
            AppealEvidenceReingestionModel.tenant_id==self.tenant_id,AppealEvidenceReingestionModel.appeal_id==appeal_id,
            AppealEvidenceReingestionModel.source_kind==source_kind,AppealEvidenceReingestionModel.source_id==source_id,
            AppealEvidenceReingestionModel.source_version==source_version,
        ))

    def comparisons(self,appeal_id:str,snapshot_id:str|None=None):
        stmt=select(AppealEvidenceComparisonModel).where(AppealEvidenceComparisonModel.tenant_id==self.tenant_id,AppealEvidenceComparisonModel.appeal_id==appeal_id)
        if snapshot_id: stmt=stmt.where(AppealEvidenceComparisonModel.snapshot_id==snapshot_id)
        return list(self.session.scalars(stmt.order_by(AppealEvidenceComparisonModel.created_at,AppealEvidenceComparisonModel.comparison_id)))

    def rag_runs(self,appeal_id:str):
        return list(self.session.scalars(select(AppealRAGRunModel).where(AppealRAGRunModel.tenant_id==self.tenant_id,AppealRAGRunModel.appeal_id==appeal_id).order_by(AppealRAGRunModel.created_at.desc())))

    def rag_items(self,run_id:str):
        return list(self.session.scalars(select(AppealRAGItemModel).where(AppealRAGItemModel.tenant_id==self.tenant_id,AppealRAGItemModel.run_id==run_id).order_by(AppealRAGItemModel.rank)))

    def recommendations(self,appeal_id:str):
        return list(self.session.scalars(select(AppealReconsiderationRunModel).where(AppealReconsiderationRunModel.tenant_id==self.tenant_id,AppealReconsiderationRunModel.appeal_id==appeal_id).order_by(AppealReconsiderationRunModel.created_at.desc())))

    def checkpoints(self,appeal_id:str):
        return list(self.session.scalars(select(AppealReconsiderationCheckpointModel).where(AppealReconsiderationCheckpointModel.tenant_id==self.tenant_id,AppealReconsiderationCheckpointModel.appeal_id==appeal_id).order_by(AppealReconsiderationCheckpointModel.created_at)))

    def next_checkpoint_version(self,thread_id:str)->int:
        n=self.session.scalar(select(func.max(AppealReconsiderationCheckpointModel.checkpoint_version)).where(AppealReconsiderationCheckpointModel.tenant_id==self.tenant_id,AppealReconsiderationCheckpointModel.thread_id==thread_id))
        return int(n or 0)+1

    def annotations(self,appeal_id:str):
        return list(self.session.scalars(select(AppealReviewerAnnotationModel).where(AppealReviewerAnnotationModel.tenant_id==self.tenant_id,AppealReviewerAnnotationModel.appeal_id==appeal_id).order_by(AppealReviewerAnnotationModel.created_at)))

    def missing_requests(self,appeal_id:str):
        return list(self.session.scalars(select(AppealMissingEvidenceRequestModel).where(AppealMissingEvidenceRequestModel.tenant_id==self.tenant_id,AppealMissingEvidenceRequestModel.appeal_id==appeal_id).order_by(AppealMissingEvidenceRequestModel.created_at)))

    def escalations(self,appeal_id:str):
        return list(self.session.scalars(select(AppealEscalationModel).where(AppealEscalationModel.tenant_id==self.tenant_id,AppealEscalationModel.appeal_id==appeal_id).order_by(AppealEscalationModel.created_at)))
