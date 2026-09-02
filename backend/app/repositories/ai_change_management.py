from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.evaluation import EvaluationRunModel, EvaluationBaselineModel
from app.models.ai_change_management import (
    AIConfigurationSnapshotModel, AIEnvironmentAssignmentModel, AIConfigurationPromotionModel,
    AIExperimentModel, AIExperimentAssignmentModel, AIExperimentObservationModel,
    AIConfigurationDriftEventModel, AIChangeEventModel,
)


class AIChangeManagementRepository:
    def __init__(self, session: Session, tenant_id: str):
        self.session = session
        self.tenant_id = tenant_id

    def add(self, model):
        self.session.add(model)
        self.session.flush()
        return model

    def snapshot(self, snapshot_id: str):
        return self.session.scalar(select(AIConfigurationSnapshotModel).where(
            AIConfigurationSnapshotModel.tenant_id == self.tenant_id,
            AIConfigurationSnapshotModel.snapshot_id == snapshot_id,
        ))

    def snapshots(self, limit: int = 100):
        return list(self.session.scalars(select(AIConfigurationSnapshotModel).where(
            AIConfigurationSnapshotModel.tenant_id == self.tenant_id,
        ).order_by(AIConfigurationSnapshotModel.created_at.desc()).limit(limit)))

    def assignment(self, environment: str, config_key: str):
        return self.session.scalar(select(AIEnvironmentAssignmentModel).where(
            AIEnvironmentAssignmentModel.tenant_id == self.tenant_id,
            AIEnvironmentAssignmentModel.environment == environment,
            AIEnvironmentAssignmentModel.config_key == config_key,
        ))

    def upsert_assignment(self, *, assignment_id: str, environment: str, config_key: str, snapshot_id: str, actor: str, activated_at, source: str):
        current = self.assignment(environment, config_key)
        if current is None:
            current = AIEnvironmentAssignmentModel(
                assignment_id=assignment_id, tenant_id=self.tenant_id, environment=environment,
                config_key=config_key, snapshot_id=snapshot_id, assignment_version=1,
                source=source, activated_by=actor, activated_at=activated_at,
            )
            self.session.add(current)
        else:
            current.snapshot_id = snapshot_id
            current.assignment_version += 1
            current.source = source
            current.activated_by = actor
            current.activated_at = activated_at
        self.session.flush()
        return current

    def promotion(self, promotion_id: str):
        return self.session.scalar(select(AIConfigurationPromotionModel).where(
            AIConfigurationPromotionModel.tenant_id == self.tenant_id,
            AIConfigurationPromotionModel.promotion_id == promotion_id,
        ))


    def evaluation_run(self, run_id: str):
        return self.session.scalar(select(EvaluationRunModel).where(
            EvaluationRunModel.tenant_id == self.tenant_id,
            EvaluationRunModel.run_id == run_id,
        ))

    def evaluation_baseline(self, baseline_id: str):
        return self.session.scalar(select(EvaluationBaselineModel).where(
            EvaluationBaselineModel.tenant_id == self.tenant_id,
            EvaluationBaselineModel.baseline_id == baseline_id,
        ))

    def previously_activated(self, *, environment: str, config_key: str, snapshot_id: str) -> bool:
        row = self.session.scalar(select(AIConfigurationPromotionModel.promotion_id).where(
            AIConfigurationPromotionModel.tenant_id == self.tenant_id,
            AIConfigurationPromotionModel.target_environment == environment,
            AIConfigurationPromotionModel.config_key == config_key,
            AIConfigurationPromotionModel.snapshot_id == snapshot_id,
            AIConfigurationPromotionModel.status == "activated",
        ).limit(1))
        return row is not None

    def experiments(self, limit: int = 100):
        return list(self.session.scalars(select(AIExperimentModel).where(
            AIExperimentModel.tenant_id == self.tenant_id,
        ).order_by(AIExperimentModel.created_at.desc()).limit(limit)))

    def experiment(self, experiment_id: str):
        return self.session.scalar(select(AIExperimentModel).where(
            AIExperimentModel.tenant_id == self.tenant_id,
            AIExperimentModel.experiment_id == experiment_id,
        ))

    def experiment_assignment(self, experiment_id: str, subject_sha256: str):
        return self.session.scalar(select(AIExperimentAssignmentModel).where(
            AIExperimentAssignmentModel.tenant_id == self.tenant_id,
            AIExperimentAssignmentModel.experiment_id == experiment_id,
            AIExperimentAssignmentModel.subject_sha256 == subject_sha256,
        ))

    def observations(self, experiment_id: str):
        return list(self.session.scalars(select(AIExperimentObservationModel).where(
            AIExperimentObservationModel.tenant_id == self.tenant_id,
            AIExperimentObservationModel.experiment_id == experiment_id,
        )))

    def drift_events(self, limit: int = 100):
        return list(self.session.scalars(select(AIConfigurationDriftEventModel).where(
            AIConfigurationDriftEventModel.tenant_id == self.tenant_id,
        ).order_by(AIConfigurationDriftEventModel.created_at.desc()).limit(limit)))

    def events(self, limit: int = 100):
        return list(self.session.scalars(select(AIChangeEventModel).where(
            AIChangeEventModel.tenant_id == self.tenant_id,
        ).order_by(AIChangeEventModel.created_at.desc()).limit(limit)))
