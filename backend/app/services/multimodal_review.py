from __future__ import annotations
import hashlib
from datetime import UTC, datetime
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.multimodal_review import ReviewAnnotationTarget
from app.models.claims import EvidenceArtifactModel
from app.models.document_intelligence import ExtractionUnitModel
from app.models.fhir import FHIRResourceSnapshotModel
from app.models.multimodal_agent_orchestration import MultimodalAgentInvestigationModel
from app.models.multimodal_rag import MultimodalEvidencePackModel, MultimodalInconsistencyModel, MultimodalRAGItemModel, MultimodalRAGRunModel
from app.models.orchestration import AgentFindingModel, AgentHumanCheckpointModel, AgentWorkflowModel
from app.models.multimodal_review import MultimodalReviewAnnotationModel
from app.repositories.multimodal_review import MultimodalReviewRepository
from app.services.review_workbench import ReviewWorkbenchService, ReviewConflictError


def _now() -> datetime:
    return datetime.now(UTC)


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class MultimodalReviewService:
    def __init__(self, session: Session, tenant_id: str):
        self.session = session
        self.tenant_id = tenant_id
        self.repo = MultimodalReviewRepository(session, tenant_id)

    def _claim_evidence(self, claim_id: str, evidence_id: str) -> EvidenceArtifactModel:
        row = self.session.scalar(select(EvidenceArtifactModel).where(
            EvidenceArtifactModel.tenant_id == self.tenant_id,
            EvidenceArtifactModel.claim_id == claim_id,
            EvidenceArtifactModel.evidence_id == evidence_id,
        ))
        if row is None:
            raise LookupError("evidence not found in claim")
        return row

    def _validate_target(self, claim_id: str, target_type: str, target_id: str) -> None:
        model = None
        if target_type == ReviewAnnotationTarget.EVIDENCE.value:
            self._claim_evidence(claim_id, target_id); return
        if target_type == ReviewAnnotationTarget.MULTIMODAL_ITEM.value:
            model = self.session.scalar(select(MultimodalRAGItemModel).where(
                MultimodalRAGItemModel.tenant_id == self.tenant_id,
                MultimodalRAGItemModel.claim_id == claim_id,
                MultimodalRAGItemModel.item_id == target_id,
            ).limit(1))
        elif target_type == ReviewAnnotationTarget.INCONSISTENCY.value:
            model = self.session.scalar(select(MultimodalInconsistencyModel).where(
                MultimodalInconsistencyModel.tenant_id == self.tenant_id,
                MultimodalInconsistencyModel.claim_id == claim_id,
                MultimodalInconsistencyModel.inconsistency_id == target_id,
            ))
        elif target_type == ReviewAnnotationTarget.AGENT_FINDING.value:
            model = self.session.scalar(select(AgentFindingModel).where(
                AgentFindingModel.tenant_id == self.tenant_id,
                AgentFindingModel.claim_id == claim_id,
                AgentFindingModel.finding_id == target_id,
            ))
        elif target_type == ReviewAnnotationTarget.CHECKPOINT.value:
            model = self.session.scalar(select(AgentHumanCheckpointModel).where(
                AgentHumanCheckpointModel.tenant_id == self.tenant_id,
                AgentHumanCheckpointModel.claim_id == claim_id,
                AgentHumanCheckpointModel.checkpoint_id == target_id,
            ))
        else:
            raise ReviewConflictError("unsupported annotation target")
        if model is None:
            raise LookupError("annotation target not found in claim")

    def add_annotation(self, claim_id: str, reviewer_user_id: str, lock_token: str, *, target_type: str, target_id: str, annotation_kind: str, anchor: dict, body: str, tags: list[str], idempotency_key: str, trace_id: str | None = None):
        ReviewWorkbenchService(self.session, self.tenant_id).verify_lock(claim_id, reviewer_user_id, lock_token)
        prior = self.repo.by_idempotency(idempotency_key)
        if prior:
            return prior
        self._validate_target(claim_id, target_type, target_id)
        row = self.repo.add(MultimodalReviewAnnotationModel(
            annotation_id=f"mra_{uuid4().hex}", tenant_id=self.tenant_id, claim_id=claim_id,
            reviewer_user_id=reviewer_user_id, target_type=target_type, target_id=target_id,
            annotation_kind=annotation_kind, anchor=anchor, body=body, body_sha256=_sha(body),
            tags=list(dict.fromkeys(tags)), idempotency_key=idempotency_key, trace_id=trace_id, created_at=_now(),
        ))
        ReviewWorkbenchService(self.session, self.tenant_id)._event(
            claim_id, reviewer_user_id, "review.multimodal.annotation.added", f"multimodal-annotation:{idempotency_key}",
            {"annotation_id": row.annotation_id, "target_type": target_type, "target_id": target_id, "annotation_kind": annotation_kind},
            trace_id=trace_id,
        )
        return row

    def render_pdf_page(self, claim_id: str, evidence_id: str, *, storage, bucket_name: str, page_number: int, bbox: list[float] | None = None) -> bytes:
        evidence = self._claim_evidence(claim_id, evidence_id)
        if evidence.media_type != "application/pdf":
            raise ReviewConflictError("page preview is available only for PDF evidence")
        if evidence.status not in {"ready", "accepted", "processed"}:
            raise ReviewConflictError("evidence is not available for reviewer preview")
        if evidence.byte_size > 50_000_000:
            raise ReviewConflictError("PDF exceeds reviewer preview size limit")
        try:
            import fitz  # type: ignore
        except ImportError as exc:
            raise RuntimeError("PyMuPDF is required for reviewer PDF page previews") from exc
        raw = b"".join(storage.iter_object_chunks(bucket=bucket_name, key=evidence.object_key))
        doc = fitz.open(stream=raw, filetype="pdf")
        try:
            index = max(0, page_number - 1)
            if index >= doc.page_count:
                raise ReviewConflictError("requested PDF page is outside the document")
            page = doc.load_page(index)
            if bbox and len(bbox) == 4:
                x0, y0, x1, y1 = [float(v) for v in bbox]
                if max(abs(x0), abs(y0), abs(x1), abs(y1)) <= 1.0:
                    x0, x1 = x0 * page.rect.width, x1 * page.rect.width
                    y0, y1 = y0 * page.rect.height, y1 * page.rect.height
                rect = fitz.Rect(x0, y0, x1, y1)
                annot = page.add_rect_annot(rect)
                annot.set_colors(stroke=(1.0, 0.65, 0.0), fill=(1.0, 0.85, 0.25))
                annot.set_opacity(0.28); annot.set_border(width=2); annot.update()
            pix = page.get_pixmap(matrix=fitz.Matrix(1.6, 1.6), alpha=False, annots=True)
            return pix.tobytes("png")
        finally:
            doc.close()

    def evidence_access(self, claim_id: str, evidence_id: str, *, storage, bucket_name: str, expires_seconds: int = 300) -> dict[str, object]:
        evidence = self._claim_evidence(claim_id, evidence_id)
        if evidence.status not in {"ready", "accepted", "processed"}:
            raise ReviewConflictError("evidence is not available for reviewer preview")
        url = storage.create_presigned_download(
            bucket=bucket_name, key=evidence.object_key, expires_seconds=min(max(expires_seconds, 60), 600),
            response_content_type=evidence.media_type,
        )
        return {
            "evidence_id": evidence.evidence_id, "media_type": evidence.media_type,
            "document_type": evidence.document_type, "url": url,
            "expires_in_seconds": min(max(expires_seconds, 60), 600), "content_sha256": evidence.content_sha256,
        }

    def snapshot(self, claim_id: str) -> dict[str, object]:
        latest_pack = self.session.scalar(select(MultimodalEvidencePackModel).where(
            MultimodalEvidencePackModel.tenant_id == self.tenant_id,
            MultimodalEvidencePackModel.claim_id == claim_id,
        ).order_by(MultimodalEvidencePackModel.created_at.desc()).limit(1))
        latest_run = None; items = []; inconsistencies = []
        if latest_pack:
            latest_run = self.session.scalar(select(MultimodalRAGRunModel).where(
                MultimodalRAGRunModel.tenant_id == self.tenant_id,
                MultimodalRAGRunModel.run_id == latest_pack.run_id,
            ))
            items = list(self.session.scalars(select(MultimodalRAGItemModel).where(
                MultimodalRAGItemModel.tenant_id == self.tenant_id,
                MultimodalRAGItemModel.pack_id == latest_pack.pack_id,
            ).order_by(MultimodalRAGItemModel.rank)))
            inconsistencies = list(self.session.scalars(select(MultimodalInconsistencyModel).where(
                MultimodalInconsistencyModel.tenant_id == self.tenant_id,
                MultimodalInconsistencyModel.pack_id == latest_pack.pack_id,
            ).order_by(MultimodalInconsistencyModel.created_at)))
        workflow = self.session.scalar(select(AgentWorkflowModel).where(
            AgentWorkflowModel.tenant_id == self.tenant_id, AgentWorkflowModel.claim_id == claim_id,
        ).order_by(AgentWorkflowModel.created_at.desc()).limit(1))
        investigations = []
        checkpoint = None
        if workflow:
            investigations = list(self.session.scalars(select(MultimodalAgentInvestigationModel).where(
                MultimodalAgentInvestigationModel.tenant_id == self.tenant_id,
                MultimodalAgentInvestigationModel.workflow_id == workflow.workflow_id,
            ).order_by(MultimodalAgentInvestigationModel.created_at)))
            checkpoint = self.session.scalar(select(AgentHumanCheckpointModel).where(
                AgentHumanCheckpointModel.tenant_id == self.tenant_id,
                AgentHumanCheckpointModel.workflow_id == workflow.workflow_id,
            ).order_by(AgentHumanCheckpointModel.created_at.desc()).limit(1))
        findings = list(self.session.scalars(select(AgentFindingModel).where(
            AgentFindingModel.tenant_id == self.tenant_id,
            AgentFindingModel.claim_id == claim_id,
        ).order_by(AgentFindingModel.created_at)))
        annotations = self.repo.list_for_claim(claim_id)
        extraction_ids = {str((i.citation or {}).get("extraction_unit_id")) for i in items if (i.citation or {}).get("extraction_unit_id")}
        extraction_by_id = {}
        if extraction_ids:
            extraction_by_id = {u.unit_id: u for u in self.session.scalars(select(ExtractionUnitModel).where(
                ExtractionUnitModel.tenant_id == self.tenant_id,
                ExtractionUnitModel.claim_id == claim_id,
                ExtractionUnitModel.unit_id.in_(extraction_ids),
            ))}
        fhir_ids = {str((i.citation or {}).get("fhir_snapshot_id")) for i in items if (i.citation or {}).get("fhir_snapshot_id")}
        fhir_by_id = {}
        if fhir_ids:
            fhir_by_id = {x.snapshot_id: x for x in self.session.scalars(select(FHIRResourceSnapshotModel).where(
                FHIRResourceSnapshotModel.tenant_id == self.tenant_id,
                FHIRResourceSnapshotModel.claim_id == claim_id,
                FHIRResourceSnapshotModel.snapshot_id.in_(fhir_ids),
            ))}
        evidence_ids = {str((i.citation or {}).get("evidence_id")) for i in items if (i.citation or {}).get("evidence_id")}
        evidence_by_id = {}
        if evidence_ids:
            evidence_by_id = {e.evidence_id: e for e in self.session.scalars(select(EvidenceArtifactModel).where(
                EvidenceArtifactModel.tenant_id == self.tenant_id,
                EvidenceArtifactModel.claim_id == claim_id,
                EvidenceArtifactModel.evidence_id.in_(evidence_ids),
            ))}
        item_rows = []
        for i in items:
            c = dict(i.citation or {})
            unit = extraction_by_id.get(str(c.get("extraction_unit_id")))
            fhir_snapshot = fhir_by_id.get(str(c.get("fhir_snapshot_id")))
            evidence = evidence_by_id.get(str(c.get("evidence_id")))
            item_rows.append({
                "item_id": i.item_id, "evidence_key": f"mm:{i.item_id}", "modality": i.modality,
                "domain": i.domain, "source_id": i.source_id, "source_version": i.source_version,
                "content_sha256": i.content_sha256, "rank": i.rank, "score": i.score,
                "confidence": i.confidence, "authority_rank": i.authority_rank,
                "citation": c, "metadata": i.metadata_summary or {}, "retrieval_sources": i.retrieval_sources or [],
                "evidence_id": c.get("evidence_id"),
                "media_type": evidence.media_type if evidence else None,
                "document_type": evidence.document_type if evidence else None,
                "display_text": unit.text_content if unit else None,
                "structured_data": unit.structured_data if unit else {},
                "fhir_resource": None if fhir_snapshot is None else {
                    "snapshot_id": fhir_snapshot.snapshot_id, "resource_type": fhir_snapshot.resource_type,
                    "logical_id": fhir_snapshot.logical_id, "version_id": fhir_snapshot.version_id,
                    "last_updated": fhir_snapshot.last_updated, "content_sha256": fhir_snapshot.content_sha256,
                    "canonical_resource": fhir_snapshot.canonical_resource, "raw_resource": fhir_snapshot.raw_resource,
                },
            })
        item_by_key = {row["evidence_key"]: row for row in item_rows}
        finding_rows=[]
        for f in findings:
            mm_keys=[key for key in (f.evidence_keys or []) if str(key).startswith("mm:")]
            if not mm_keys and not (f.finding_metadata or {}).get("multimodal_citations"):
                continue
            finding_rows.append({
                "finding_id": f.finding_id, "agent_name": f.agent_name, "confidence": f.confidence,
                "requires_human_review": f.requires_human_review, "risk_flags": f.risk_flags or [],
                "evidence_keys": f.evidence_keys or [], "multimodal_evidence": [item_by_key[k] for k in mm_keys if k in item_by_key],
                "metadata": f.finding_metadata or {}, "created_at": f.created_at,
            })
        return {
            "latest_pack": None if latest_pack is None else {
                "pack_id": latest_pack.pack_id, "run_id": latest_pack.run_id, "pack_sha256": latest_pack.pack_sha256,
                "modalities": latest_pack.modalities or [], "confidence": latest_pack.confidence,
                "modality_coverage": latest_pack.modality_coverage, "citation_coverage": latest_pack.citation_coverage,
                "answerability": latest_pack.answerability, "intent": latest_run.intent if latest_run else None,
                "created_at": latest_pack.created_at,
            },
            "items": item_rows,
            "inconsistencies": [{
                "inconsistency_id": x.inconsistency_id, "code": x.code, "field": x.field,
                "severity": x.severity, "left_item_id": x.left_item_id, "right_item_id": x.right_item_id,
                "confidence": x.confidence, "human_review_required": x.human_review_required, "created_at": x.created_at,
            } for x in inconsistencies],
            "investigations": [{
                "investigation_id": x.investigation_id, "agent_name": x.agent_name, "attempt": x.attempt,
                "pack_id": x.pack_id, "pack_sha256": x.pack_sha256, "answerability": x.answerability,
                "confidence": x.confidence, "requested_modalities": x.requested_modalities or [],
                "required_modalities": x.required_modalities or [], "material_inconsistency_count": x.material_inconsistency_count,
                "blocking_gap_count": x.blocking_gap_count, "human_review_required": x.human_review_required,
                "escalation_reasons": x.escalation_reasons or [], "trace_id": x.trace_id, "created_at": x.created_at,
            } for x in investigations],
            "agent_findings": finding_rows,
            "checkpoint": None if checkpoint is None else {
                "checkpoint_id": checkpoint.checkpoint_id, "workflow_id": checkpoint.workflow_id,
                "reason": checkpoint.reason, "status": checkpoint.status,
                "required_permissions": checkpoint.required_permissions or [], "metadata": checkpoint.checkpoint_metadata or {},
                "created_at": checkpoint.created_at, "resumed_at": checkpoint.resumed_at,
            },
            "annotations": [{
                "annotation_id": a.annotation_id, "reviewer_user_id": a.reviewer_user_id,
                "target_type": a.target_type, "target_id": a.target_id, "annotation_kind": a.annotation_kind,
                "anchor": a.anchor or {}, "body": a.body, "tags": a.tags or [], "created_at": a.created_at,
            } for a in annotations],
            "traceability": {
                "multimodal_item_count": len(item_rows), "investigation_count": len(investigations),
                "finding_count": len(finding_rows), "annotation_count": len(annotations),
                "final_decision_human_only": True,
            },
        }
