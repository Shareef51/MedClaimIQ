from __future__ import annotations
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.performance_resilience import PerformanceRunModel, PerformanceMetricModel, ResilienceExperimentModel, CapacitySnapshotModel


class PerformanceResilienceRepository:
    def __init__(self, session: Session, tenant_id: str):
        self.session = session
        self.tenant_id = tenant_id

    def runs(self, limit: int = 50):
        return list(self.session.scalars(select(PerformanceRunModel).where(PerformanceRunModel.tenant_id == self.tenant_id).order_by(PerformanceRunModel.started_at.desc()).limit(limit)))

    def metrics(self, run_id: str):
        return list(self.session.scalars(select(PerformanceMetricModel).where(PerformanceMetricModel.tenant_id == self.tenant_id, PerformanceMetricModel.run_id == run_id).order_by(PerformanceMetricModel.metric_key)))

    def experiments(self, limit: int = 50):
        return list(self.session.scalars(select(ResilienceExperimentModel).where(ResilienceExperimentModel.tenant_id == self.tenant_id).order_by(ResilienceExperimentModel.started_at.desc()).limit(limit)))

    def capacity(self, limit: int = 20):
        return list(self.session.scalars(select(CapacitySnapshotModel).where(CapacitySnapshotModel.tenant_id == self.tenant_id).order_by(CapacitySnapshotModel.created_at.desc()).limit(limit)))
