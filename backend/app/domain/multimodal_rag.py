from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from app.domain.advanced_rag import Answerability
from app.domain.orchestration import AgentName
from app.domain.rag import RAGDomain


class EvidenceModality(StrEnum):
    TEXT = "text"
    DOCUMENT = "document"
    TABLE = "table"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    FHIR = "fhir"


class MultimodalIntent(StrEnum):
    GENERAL_EVIDENCE = "general_evidence"
    DOCUMENT_VISUAL = "document_visual"
    INVOICE_VERIFICATION = "invoice_verification"
    AUDIO_VERIFICATION = "audio_verification"
    VIDEO_TIMELINE = "video_timeline"
    FHIR_CROSS_CHECK = "fhir_cross_check"
    CROSS_MODAL_VERIFICATION = "cross_modal_verification"


class InconsistencySeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    MATERIAL = "material"


@dataclass(frozen=True, slots=True)
class MultimodalCitation:
    modality: EvidenceModality
    evidence_id: str | None = None
    extraction_unit_id: str | None = None
    page_number: int | None = None
    bbox: tuple[float, float, float, float] | None = None
    start_ms: int | None = None
    end_ms: int | None = None
    frame_index: int | None = None
    frame_sha256: str | None = None
    fhir_snapshot_id: str | None = None
    fhir_resource_type: str | None = None
    fhir_logical_id: str | None = None
    fhir_version_id: str | None = None
    source_locator: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> tuple[bool, tuple[str, ...]]:
        reasons: list[str] = []
        if self.modality in {EvidenceModality.DOCUMENT, EvidenceModality.TABLE, EvidenceModality.IMAGE} and not self.evidence_id:
            reasons.append("missing_evidence_id")
        if self.modality == EvidenceModality.IMAGE and self.bbox is None and not self.source_locator:
            reasons.append("missing_image_locator")
        if self.modality == EvidenceModality.AUDIO and (self.start_ms is None or self.end_ms is None):
            reasons.append("missing_audio_timecode")
        if self.modality == EvidenceModality.VIDEO:
            if self.start_ms is None:
                reasons.append("missing_video_timecode")
            if self.source_locator.get("kind") == "keyframe" and self.frame_index is None:
                reasons.append("missing_frame_index")
        if self.modality == EvidenceModality.FHIR:
            if not self.fhir_snapshot_id:
                reasons.append("missing_fhir_snapshot")
            if not self.fhir_resource_type or not self.fhir_logical_id or not self.fhir_version_id:
                reasons.append("missing_fhir_version_locator")
        return not reasons, tuple(reasons)

    def as_dict(self) -> dict[str, Any]:
        return {
            "modality": self.modality.value,
            "evidence_id": self.evidence_id,
            "extraction_unit_id": self.extraction_unit_id,
            "page_number": self.page_number,
            "bbox": list(self.bbox) if self.bbox else None,
            "start_ms": self.start_ms,
            "end_ms": self.end_ms,
            "frame_index": self.frame_index,
            "frame_sha256": self.frame_sha256,
            "fhir_snapshot_id": self.fhir_snapshot_id,
            "fhir_resource_type": self.fhir_resource_type,
            "fhir_logical_id": self.fhir_logical_id,
            "fhir_version_id": self.fhir_version_id,
            "source_locator": self.source_locator,
        }


@dataclass(frozen=True, slots=True)
class MultimodalRoute:
    intent: MultimodalIntent
    modalities: tuple[EvidenceModality, ...]
    required_modalities: tuple[EvidenceModality, ...]
    agent: AgentName | None = None
    reasons: tuple[str, ...] = ()
    planner_version: str = "multimodal-router-v1"


@dataclass(frozen=True, slots=True)
class MultimodalCandidate:
    item_id: str
    modality: EvidenceModality
    domain: RAGDomain
    source_id: str
    source_version: str
    text: str
    score: float
    confidence: float
    authority_rank: int
    citation: MultimodalCitation
    metadata: dict[str, Any] = field(default_factory=dict)
    retrieval_sources: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class MultimodalInconsistency:
    code: str
    field: str
    severity: InconsistencySeverity
    left_item_id: str
    right_item_id: str
    left_value: str
    right_value: str
    confidence: float
    description: str


@dataclass(frozen=True, slots=True)
class MultimodalKnowledgeGap:
    code: str
    description: str
    blocking: bool
    modality: EvidenceModality | None = None


@dataclass(frozen=True, slots=True)
class MultimodalEvidencePack:
    pack_id: str
    run_id: str
    claim_id: str
    items: tuple[MultimodalCandidate, ...]
    inconsistencies: tuple[MultimodalInconsistency, ...]
    gaps: tuple[MultimodalKnowledgeGap, ...]
    answerability: Answerability
    confidence: float
    modality_coverage: float
    citation_coverage: float
    source_diversity: float
    diagnostics: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class MultimodalRAGResult:
    run_id: str
    query: str
    route: MultimodalRoute
    pack: MultimodalEvidencePack
    latency_ms: int
    trace_id: str | None = None


def multimodal_model_contract() -> dict[str, object]:
    return {
        "architecture": "governed-cross-modal-rag",
        "modalities": [m.value for m in EvidenceModality],
        "retrieval": [
            "Advanced-RAG textual retrieval",
            "OCR/layout/table extraction-unit retrieval",
            "audio transcript timecode retrieval",
            "video transcript/keyframe timeline retrieval",
            "FHIR versioned snapshot retrieval",
            "modality-aware reranking and diversified fusion",
        ],
        "citations": ["page", "bbox", "timecode", "frame index/hash", "FHIR resource/version"],
        "verification": [
            "cross-modal amount/code/date comparison",
            "material inconsistency detection",
            "modality coverage",
            "citation coverage",
            "explicit multimodal knowledge gaps",
        ],
        "security_invariants": [
            "claim tenant and AI-findings authorization is checked before retrieval",
            "multimodal routing never broadens tenant, claim, patient, ACL, or governed knowledge scope",
            "Release 30 knowledge lifecycle remains authoritative for governed RAG chunks",
            "raw media bytes are not copied into retrieval telemetry",
            "multimodal results remain advisory and cannot finalize a claim",
        ],
    }
