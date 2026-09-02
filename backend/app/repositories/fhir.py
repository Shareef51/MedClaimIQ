from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import set_tenant_context
from app.models.fhir import (
    FHIRConnectionModel,
    FHIRResourceSnapshotModel,
    HealthcareEventModel,
    HealthcareEventOutboxModel,
    HospitalCrossVerificationModel,
    PatientIdentityMatchModel,
)


class FHIRRepository:
    def __init__(self, session: Session, tenant_id: str) -> None:
        self.session = session
        self.tenant_id = tenant_id
        set_tenant_context(session, tenant_id)

    def _guard(self, tenant_id: str) -> None:
        if tenant_id != self.tenant_id:
            raise ValueError("cross-tenant FHIR persistence denied")

    def connection(self, connection_id: str) -> FHIRConnectionModel | None:
        return self.session.scalar(select(FHIRConnectionModel).where(FHIRConnectionModel.tenant_id == self.tenant_id, FHIRConnectionModel.connection_id == connection_id))

    def add_connection(self, model: FHIRConnectionModel) -> FHIRConnectionModel:
        self._guard(model.tenant_id); self.session.add(model); self.session.flush(); return model

    def snapshot_by_version(self, connection_id: str, resource_type: str, logical_id: str, version_id: str) -> FHIRResourceSnapshotModel | None:
        return self.session.scalar(select(FHIRResourceSnapshotModel).where(
            FHIRResourceSnapshotModel.tenant_id == self.tenant_id,
            FHIRResourceSnapshotModel.connection_id == connection_id,
            FHIRResourceSnapshotModel.resource_type == resource_type,
            FHIRResourceSnapshotModel.logical_id == logical_id,
            FHIRResourceSnapshotModel.version_id == version_id,
        ))

    def add_snapshot(self, model: FHIRResourceSnapshotModel) -> FHIRResourceSnapshotModel:
        self._guard(model.tenant_id); self.session.add(model); self.session.flush(); return model

    def add_identity_match(self, model: PatientIdentityMatchModel) -> PatientIdentityMatchModel:
        self._guard(model.tenant_id); self.session.add(model); self.session.flush(); return model

    def add_verification(self, model: HospitalCrossVerificationModel) -> HospitalCrossVerificationModel:
        self._guard(model.tenant_id); self.session.add(model); self.session.flush(); return model

    def add_event(self, event: HealthcareEventModel, outbox: HealthcareEventOutboxModel) -> None:
        self._guard(event.tenant_id); self._guard(outbox.tenant_id)
        self.session.add(event); self.session.flush(); self.session.add(outbox); self.session.flush()
