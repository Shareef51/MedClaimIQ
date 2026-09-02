from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import set_tenant_context
from app.models.ingestion import (
    EvidenceEventOutboxModel,
    EvidenceProcessingEventModel,
    EvidenceUploadSessionModel,
    MalwareScanModel,
)


class _TenantRepository:
    def __init__(self, session: Session, tenant_id: str) -> None:
        self.session = session
        self.tenant_id = tenant_id
        set_tenant_context(session, tenant_id)

    def _ensure_tenant(self, row_tenant_id: str) -> None:
        if row_tenant_id != self.tenant_id:
            raise ValueError("row tenant does not match repository tenant context")


class UploadSessionRepository(_TenantRepository):
    def get(self, upload_session_id: str) -> EvidenceUploadSessionModel | None:
        return self.session.scalar(
            select(EvidenceUploadSessionModel).where(
                EvidenceUploadSessionModel.tenant_id == self.tenant_id,
                EvidenceUploadSessionModel.upload_session_id == upload_session_id,
            )
        )

    def get_for_update(self, upload_session_id: str) -> EvidenceUploadSessionModel | None:
        return self.session.scalar(
            select(EvidenceUploadSessionModel)
            .where(
                EvidenceUploadSessionModel.tenant_id == self.tenant_id,
                EvidenceUploadSessionModel.upload_session_id == upload_session_id,
            )
            .with_for_update()
        )

    def get_by_idempotency(self, idempotency_key: str) -> EvidenceUploadSessionModel | None:
        return self.session.scalar(
            select(EvidenceUploadSessionModel).where(
                EvidenceUploadSessionModel.tenant_id == self.tenant_id,
                EvidenceUploadSessionModel.idempotency_key == idempotency_key,
            )
        )

    def add(self, model: EvidenceUploadSessionModel) -> EvidenceUploadSessionModel:
        self._ensure_tenant(model.tenant_id)
        self.session.add(model)
        self.session.flush()
        return model


class MalwareScanRepository(_TenantRepository):
    def add(self, model: MalwareScanModel) -> MalwareScanModel:
        self._ensure_tenant(model.tenant_id)
        self.session.add(model)
        self.session.flush()
        return model

    def count_attempts(self, upload_session_id: str) -> int:
        return len(
            list(
                self.session.scalars(
                    select(MalwareScanModel).where(
                        MalwareScanModel.tenant_id == self.tenant_id,
                        MalwareScanModel.upload_session_id == upload_session_id,
                    )
                )
            )
        )


class ProcessingEventRepository(_TenantRepository):
    def get_by_idempotency(self, idempotency_key: str) -> EvidenceProcessingEventModel | None:
        return self.session.scalar(
            select(EvidenceProcessingEventModel).where(
                EvidenceProcessingEventModel.tenant_id == self.tenant_id,
                EvidenceProcessingEventModel.idempotency_key == idempotency_key,
            )
        )

    def add(self, model: EvidenceProcessingEventModel) -> EvidenceProcessingEventModel:
        self._ensure_tenant(model.tenant_id)
        self.session.add(model)
        self.session.flush()
        return model

    def list_for_aggregate(self, aggregate_id: str) -> list[EvidenceProcessingEventModel]:
        return list(
            self.session.scalars(
                select(EvidenceProcessingEventModel)
                .where(
                    EvidenceProcessingEventModel.tenant_id == self.tenant_id,
                    EvidenceProcessingEventModel.aggregate_id == aggregate_id,
                )
                .order_by(EvidenceProcessingEventModel.occurred_at, EvidenceProcessingEventModel.event_id)
            )
        )


class EvidenceOutboxRepository(_TenantRepository):
    def add(self, model: EvidenceEventOutboxModel) -> EvidenceEventOutboxModel:
        self._ensure_tenant(model.tenant_id)
        self.session.add(model)
        self.session.flush()
        return model

    def list_pending(self, *, now: datetime, limit: int = 100) -> list[EvidenceEventOutboxModel]:
        return list(
            self.session.scalars(
                select(EvidenceEventOutboxModel)
                .where(
                    EvidenceEventOutboxModel.tenant_id == self.tenant_id,
                    EvidenceEventOutboxModel.status == "pending",
                    EvidenceEventOutboxModel.available_at <= now,
                )
                .order_by(EvidenceEventOutboxModel.created_at)
                .limit(limit)
            )
        )
