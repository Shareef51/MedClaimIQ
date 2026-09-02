from __future__ import annotations
from enum import StrEnum


class ReviewAnnotationTarget(StrEnum):
    EVIDENCE = "evidence"
    MULTIMODAL_ITEM = "multimodal_item"
    INCONSISTENCY = "inconsistency"
    AGENT_FINDING = "agent_finding"
    CHECKPOINT = "checkpoint"


class ReviewAnnotationKind(StrEnum):
    NOTE = "note"
    HIGHLIGHT = "highlight"
    QUESTION = "question"
    RESOLUTION = "resolution"


def multimodal_reviewer_contract() -> dict[str, object]:
    return {
        "viewer": {
            "document": ["page_number", "bbox"],
            "image": ["bbox", "content_sha256"],
            "table": ["page_number", "bbox", "row", "column"],
            "audio": ["start_ms", "end_ms"],
            "video": ["start_ms", "end_ms", "frame_index", "frame_sha256"],
            "fhir": ["fhir_resource_type", "fhir_logical_id", "fhir_version_id", "fhir_snapshot_id"],
        },
        "traceability": [
            "multimodal evidence item -> citation anchor -> source evidence",
            "agent investigation -> multimodal evidence pack -> evidence items",
            "human checkpoint -> escalation reason -> multimodal investigation",
            "review annotation -> exact target + anchor",
        ],
        "safety": {
            "final_claim_decision_is_human_only": True,
            "viewer_does_not_mutate_evidence": True,
            "signed_media_access_is_claim_scoped": True,
            "annotation_requires_active_review_lease": True,
            "raw_object_keys_not_returned_to_browser": True,
        },
        "realtime": {"claim_sse": "/api/v1/claims/{claim_id}/realtime/events"},
    }
