from __future__ import annotations

KNOWLEDGE_GOVERNANCE_AUTHORITY = {
    "recommendation_only": True,
    "ai_can_retrieve_regulatory_evidence": True,
    "ai_can_map_supervisory_relationships": True,
    "ai_can_detect_stale_or_conflicting_knowledge": True,
    "ai_can_simulate_examination_questions": True,
    "ai_can_classify_authoritative_regulatory_interpretation": False,
    "ai_can_publish_authoritative_knowledge": False,
    "ai_can_approve_policy_or_control_changes": False,
    "ai_can_certify_controls": False,
    "ai_can_close_findings": False,
    "ai_can_accept_residual_risk": False,
    "worker_can_publish_knowledge_release": False,
    "worker_can_modify_accounting_records": False,
    "worker_can_authorize_payments": False,
    "worker_can_collect_or_move_money": False,
    "human_approval_required_for_authoritative_knowledge": True,
    "human_validation_required_for_examination_answers": True,
}

KNOWLEDGE_CLASSES = ("authoritative", "approved_internal", "advisory", "historical", "superseded")
NODE_TYPES = ("regulator", "examination", "obligation", "finding", "lesson", "root_cause", "control", "policy", "procedure", "evidence")
EDGE_TYPES = (
    "REQUIRES", "IDENTIFIED_IN", "REMEDIATED_BY", "SUPPORTED_BY", "DERIVED_FROM",
    "IMPLEMENTS", "SUPERSEDES", "CONFLICTS_WITH", "APPLIES_TO_ENTITY", "SHARES_ROOT_CAUSE"
)


def knowledge_governance_contract() -> dict:
    return {
        "name": "production_regulatory_remediation_enterprise_knowledge_governance_supervisory_graph_and_examination_readiness",
        "knowledge_classes": KNOWLEDGE_CLASSES,
        "node_types": NODE_TYPES,
        "edge_types": EDGE_TYPES,
        "capabilities": [
            "lesson_to_control_to_obligation_graph",
            "temporal_version_aware_graph_rag",
            "authoritative_vs_advisory_classification",
            "policy_and_control_lineage",
            "stale_knowledge_detection",
            "conflicting_guidance_detection",
            "examination_readiness_evidence_packs",
            "regulatory_question_simulation",
            "historical_finding_retrieval",
            "cross_entity_applicability_analysis",
            "human_knowledge_approval",
            "immutable_knowledge_releases",
            "sse_readiness_events",
        ],
        "authority": KNOWLEDGE_GOVERNANCE_AUTHORITY,
        "traceability": "regulatory evidence -> approved lesson -> knowledge graph -> examination query -> cited answer -> human validation",
    }
