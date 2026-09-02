from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import set_tenant_context
from app.models.document_intelligence import DocumentExtractionRunModel, ExtractionDeadLetterModel, ExtractionUnitModel


class _TenantRepository:
    def __init__(self, session: Session, tenant_id: str) -> None:
        self.session = session
        self.tenant_id = tenant_id
        set_tenant_context(session, tenant_id)

    def _guard(self, row_tenant_id: str) -> None:
        if row_tenant_id != self.tenant_id:
            raise ValueError("row tenant does not match repository tenant context")


class DocumentExtractionRunRepository(_TenantRepository):
    def get(self, run_id: str) -> DocumentExtractionRunModel | None:
        return self.session.scalar(select(DocumentExtractionRunModel).where(DocumentExtractionRunModel.tenant_id == self.tenant_id, DocumentExtractionRunModel.run_id == run_id))

    def get_by_idempotency(self, key: str) -> DocumentExtractionRunModel | None:
        return self.session.scalar(select(DocumentExtractionRunModel).where(DocumentExtractionRunModel.tenant_id == self.tenant_id, DocumentExtractionRunModel.idempotency_key == key))

    def list_for_evidence(self, evidence_id: str) -> list[DocumentExtractionRunModel]:
        return list(self.session.scalars(select(DocumentExtractionRunModel).where(DocumentExtractionRunModel.tenant_id == self.tenant_id, DocumentExtractionRunModel.evidence_id == evidence_id).order_by(DocumentExtractionRunModel.attempt_number)))

    def add(self, model: DocumentExtractionRunModel) -> DocumentExtractionRunModel:
        self._guard(model.tenant_id); self.session.add(model); self.session.flush(); return model


class ExtractionUnitRepository(_TenantRepository):
    def add_all(self, models: list[ExtractionUnitModel]) -> list[ExtractionUnitModel]:
        for model in models: self._guard(model.tenant_id)
        self.session.add_all(models); self.session.flush(); return models

    def list_for_run(self, run_id: str) -> list[ExtractionUnitModel]:
        return list(self.session.scalars(select(ExtractionUnitModel).where(ExtractionUnitModel.tenant_id == self.tenant_id, ExtractionUnitModel.run_id == run_id).order_by(ExtractionUnitModel.sequence)))


class ExtractionDeadLetterRepository(_TenantRepository):
    def add(self, model: ExtractionDeadLetterModel) -> ExtractionDeadLetterModel:
        self._guard(model.tenant_id); self.session.add(model); self.session.flush(); return model
