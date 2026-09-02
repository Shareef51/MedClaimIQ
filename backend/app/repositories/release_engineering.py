from __future__ import annotations
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.release_engineering import ReleaseManifestModel, DeploymentRecordModel, ReleaseGateResultModel


class ReleaseEngineeringRepository:
    def __init__(self, session: Session, tenant_id: str):
        self.session = session
        self.tenant_id = tenant_id

    def manifests(self, limit: int = 50):
        return list(self.session.scalars(select(ReleaseManifestModel).where(ReleaseManifestModel.tenant_id == self.tenant_id).order_by(ReleaseManifestModel.released_at.desc()).limit(limit)))

    def deployments(self, limit: int = 100):
        return list(self.session.scalars(select(DeploymentRecordModel).where(DeploymentRecordModel.tenant_id == self.tenant_id).order_by(DeploymentRecordModel.started_at.desc()).limit(limit)))

    def gate_results(self, release_id: str):
        return list(self.session.scalars(select(ReleaseGateResultModel).where(ReleaseGateResultModel.tenant_id == self.tenant_id, ReleaseGateResultModel.release_id == release_id).order_by(ReleaseGateResultModel.gate_name)))
