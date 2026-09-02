from __future__ import annotations

LESSONS_LEARNED_AUTHORITY = {
    "recommendation_only": True,
    "ai_can_benchmark_remediation_effectiveness": True,
    "ai_can_detect_recurring_control_patterns": True,
    "ai_can_summarize_regulatory_feedback": True,
    "ai_can_propose_control_improvements": True,
    "ai_can_propose_policy_or_procedure_changes": True,
    "ai_can_update_authoritative_controls": False,
    "ai_can_modify_policy_or_procedure": False,
    "ai_can_approve_control_change": False,
    "ai_can_certify_control_effectiveness": False,
    "ai_can_close_findings": False,
    "ai_can_accept_residual_risk": False,
    "worker_can_publish_authoritative_knowledge": False,
    "worker_can_modify_accounting_records": False,
    "worker_can_authorize_payments": False,
    "worker_can_collect_or_move_money": False,
    "human_approval_required_for_control_improvement": True,
    "human_approval_required_for_knowledge_promotion": True,
}


def lessons_learned_contract() -> dict:
    return {
        "name": "production_regulatory_remediation_lessons_learned_control_improvement_and_feedback_integration",
        "scope": [
            "remediation_effectiveness_benchmarking",
            "root_cause_trend_intelligence",
            "failed_vs_successful_remediation_comparison",
            "recurring_control_pattern_detection",
            "cross_entity_lesson_propagation",
            "regulatory_feedback_ingestion",
            "supervisory_theme_mapping",
            "control_improvement_recommendations",
            "policy_and_procedure_improvement_proposals",
            "evidence_grounded_rag_learning",
            "human_approved_control_improvement_actions",
            "immutable_lessons_learned_versions",
            "sse_executive_events",
            "future_examination_evidence_traceability",
        ],
        "authority": LESSONS_LEARNED_AUTHORITY,
        "traceability": "remediation outcome -> lesson -> control improvement -> human approval -> implementation -> future examination evidence",
    }
