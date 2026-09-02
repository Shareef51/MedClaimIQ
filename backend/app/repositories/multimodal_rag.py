from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import set_tenant_context
from app.models.document_intelligence import DocumentExtractionRunModel, ExtractionUnitModel
from app.models.fhir import FHIRResourceSnapshotModel
from app.models.multimodal_rag import MultimodalEvidencePackModel, MultimodalInconsistencyModel, MultimodalRAGItemModel, MultimodalRAGRunModel


@dataclass(frozen=True)
class ExtractionSourceUnit:
    unit: ExtractionUnitModel
    media_type: str
    source_version: str


class MultimodalRAGRepository:
    def __init__(self, session: Session, *, tenant_id: str) -> None:
        self.session = session
        self.tenant_id = tenant_id
        set_tenant_context(session, tenant_id)

    def extraction_units(self, *, claim_id: str) -> list[ExtractionSourceUnit]:
        rows = self.session.execute(
            select(ExtractionUnitModel, DocumentExtractionRunModel)
            .join(DocumentExtractionRunModel, DocumentExtractionRunModel.run_id == ExtractionUnitModel.run_id)
            .where(
                ExtractionUnitModel.tenant_id == self.tenant_id,
                ExtractionUnitModel.claim_id == claim_id,
                DocumentExtractionRunModel.tenant_id == self.tenant_id,
                DocumentExtractionRunModel.status == "succeeded",
            )
            .order_by(ExtractionUnitModel.created_at.desc(), ExtractionUnitModel.sequence)
        ).all()
        return [ExtractionSourceUnit(unit=unit, media_type=run.media_type, source_version=run.pipeline_version) for unit, run in rows]

    def fhir_snapshots(self, *, claim_id: str) -> list[FHIRResourceSnapshotModel]:
        return list(self.session.scalars(
            select(FHIRResourceSnapshotModel)
            .where(FHIRResourceSnapshotModel.tenant_id == self.tenant_id, FHIRResourceSnapshotModel.claim_id == claim_id)
            .order_by(FHIRResourceSnapshotModel.fetched_at.desc())
            .limit(100)
        ))

    def add_result(
        self,
        *,
        run: MultimodalRAGRunModel,
        pack: MultimodalEvidencePackModel,
        items: list[MultimodalRAGItemModel],
        inconsistencies: list[MultimodalInconsistencyModel],
    ) -> None:
        for row in [run, pack, *items, *inconsistencies]:
            if row.tenant_id != self.tenant_id:
                raise PermissionError("cross-tenant multimodal RAG persistence denied")
        self.session.add(run)
        self.session.flush()
        self.session.add(pack)
        self.session.flush()
        self.session.add_all(items)
        self.session.add_all(inconsistencies)
        self.session.flush()

    def recent_runs(self, *, claim_id: str, limit: int = 20) -> list[MultimodalRAGRunModel]:
        return list(self.session.scalars(
            select(MultimodalRAGRunModel)
            .where(MultimodalRAGRunModel.tenant_id == self.tenant_id, MultimodalRAGRunModel.claim_id == claim_id)
            .order_by(MultimodalRAGRunModel.created_at.desc())
            .limit(max(1, min(100, limit)))
        ))
