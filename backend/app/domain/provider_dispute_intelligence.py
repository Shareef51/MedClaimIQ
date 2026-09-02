from __future__ import annotations

PROVIDER_DISPUTE_INTELLIGENCE_AUTHORITY = {
    "ai_can_analyze_dispute": True,
    "ai_can_recommend_dispute_outcome": True,
    "ai_can_adjudicate_dispute": False,
    "ai_can_change_accounting": False,
    "ai_can_authorize_payment": False,
    "ai_can_collect_funds": False,
    "llm_can_move_money": False,
    "langgraph_can_move_money": False,
    "rag_can_move_money": False,
    "mcp_can_move_money": False,
    "background_worker_can_move_money": False,
    "independent_human_resolution_required": True,
    "recommendation_only": True,
}

RECOMMENDATIONS=("uphold_recovery","consider_reduce_recovery","consider_withdraw_recovery","request_information","escalate")
COMPARISON_TYPES=("added","changed","contradictory","corroborating","unchanged")
MISSING_EVIDENCE_TYPES=("provider_agreement","fee_schedule","authorization","corrected_claim","remittance","clinical_record","itemized_bill","other")

def provider_dispute_intelligence_contract()->dict[str,object]:
    return {
        "name":"production_provider_dispute_evidence_reingestion_contract_policy_rag",
        "workflow":[
            "provider_dispute_evidence_acceptance_boundary",
            "document_image_audio_fhir_reingestion",
            "immutable_dispute_evidence_snapshot",
            "provider_agreement_and_policy_version_retrieval",
            "original_recovery_vs_provider_evidence_comparison",
            "payment_policy_contradiction_detection",
            "hybrid_dispute_rag_with_citations",
            "recommendation_only_dispute_agent",
            "durable_human_review_checkpoint",
            "missing_evidence_and_provider_response",
            "evidence_bound_independent_human_dispute_resolution_in_release46",
        ],
        "recommendations":RECOMMENDATIONS,
        "comparison_types":COMPARISON_TYPES,
        "authority":PROVIDER_DISPUTE_INTELLIGENCE_AUTHORITY,
    }
