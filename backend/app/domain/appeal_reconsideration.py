from __future__ import annotations

from enum import StrEnum


class AppealEvidenceSnapshotStatus(StrEnum):
    BUILDING = "building"
    LOCKED = "locked"
    SUPERSEDED = "superseded"


class AppealReingestionStatus(StrEnum):
    PENDING = "pending"
    VALIDATING = "validating"
    EXTRACTING = "extracting"
    INDEXING = "indexing"
    READY = "ready"
    BLOCKED = "blocked"
    FAILED = "failed"


class AppealComparisonType(StrEnum):
    ADDED = "added"
    CHANGED = "changed"
    CONTRADICTORY = "contradictory"
    CORROBORATING = "corroborating"
    UNCHANGED = "unchanged"


class ReconsiderationRecommendation(StrEnum):
    AFFIRM = "affirm"
    CONSIDER_MODIFY = "consider_modify"
    CONSIDER_OVERTURN = "consider_overturn"
    REQUEST_INFORMATION = "request_information"
    ESCALATE = "escalate"


class AppealCheckpointStatus(StrEnum):
    WAITING = "waiting"
    RESUMED = "resumed"
    CLOSED = "closed"


class AppealEscalationLevel(StrEnum):
    STANDARD = "standard"
    SECOND_LEVEL = "second_level"
    SPECIALIST = "specialist"


def appeal_reconsideration_contract() -> dict[str, object]:
    return {
        "pipeline": [
            "supplemental_evidence_linked",
            "file_and_malware_validation",
            "multimodal_reingestion",
            "version_aware_chunking",
            "embedding_and_hybrid_indexing",
            "immutable_appeal_evidence_snapshot",
            "original_vs_supplemental_comparison",
            "appeal_scoped_hybrid_retrieval",
            "contradiction_and_changed_fact_analysis",
            "recommendation_only_reconsideration_agents",
            "independent_human_appeal_review",
            "human_resolution",
        ],
        "modalities": ["document", "table", "image", "audio", "video", "fhir"],
        "retrieval": {
            "strategy": "appeal_scoped_hybrid_dense_bm25_reranked",
            "version_aware": True,
            "citation_drill_down": True,
            "original_and_supplemental_sources_separated": True,
        },
        "durability": {
            "langgraph_thread_checkpointing": True,
            "human_interrupt_before_resolution": True,
            "immutable_snapshot_hashing": True,
            "sse_progress_events": True,
        },
        "authority": {
            "reconsideration_agent_is_recommendation_only": True,
            "llm_can_affirm_modify_or_overturn": False,
            "langgraph_can_affirm_modify_or_overturn": False,
            "rag_can_affirm_modify_or_overturn": False,
            "mcp_can_affirm_modify_or_overturn": False,
            "automation_can_affirm_modify_or_overturn": False,
            "authorized_independent_human_required": True,
            "automated_financial_execution": False,
        },
        "traceability": "original evidence -> original human decision -> supplemental appeal evidence -> validated/reingested evidence -> appeal RAG citations -> recommendation-only agent -> independent human appeal resolution",
    }
