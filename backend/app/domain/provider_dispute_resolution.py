from __future__ import annotations

PROVIDER_DISPUTE_RESOLUTION_AUTHORITY={
    "ai_can_analyze":True,"ai_can_recommend":True,"ai_can_resolve_dispute":False,
    "langgraph_can_resolve_dispute":False,"rag_can_resolve_dispute":False,"mcp_can_resolve_dispute":False,
    "background_worker_can_resolve_dispute":False,"background_worker_can_change_accounting":False,
    "background_worker_can_authorize_payment":False,"background_worker_can_collect_funds":False,
    "background_worker_can_move_money":False,"independent_human_finance_approver_required":True,
    "material_dispute_dual_control_required":True,"recommendation_only":True,
}
FINAL_OUTCOMES=("uphold_recovery","reduce_recovery","withdraw_recovery")
SECOND_REVIEW_ACTIONS=("approve","reject")
MATERIAL_FINANCIAL_CHANGE_ABS=100.0
MATERIAL_FINANCIAL_CHANGE_PCT=10.0

def provider_dispute_resolution_contract()->dict[str,object]:
    return {
      "name":"production_evidence_bound_provider_dispute_resolution_and_recovery_amendment",
      "workflow":["locked_release45_snapshot","human_dispute_decision_packet","citation_and_completeness_validation","policy_conflict_resolution","recommendation_disagreement_capture","material_dual_control","resolution_version_lock","human_final_dispute_resolution","immutable_recovery_position_supersession","reversal_referral_only","regenerated_provider_correspondence","accounting_reconciliation_followup","sla_closure","sse_and_audit"],
      "blocking_rules":{"locked_snapshot_required":True,"citations_required":True,"unresolved_material_policy_conflicts_block":True,"open_missing_evidence_blocks":True,"recommendation_disagreement_requires_reason":True},
      "dual_control":{"material_dispute":True,"material_recovery_target_change":True,"second_finance_approver_must_differ":True},
      "authority":PROVIDER_DISPUTE_RESOLUTION_AUTHORITY,
      "traceability":"provider dispute evidence -> locked policy/contract snapshot -> recommendation-only analysis -> primary human packet -> second human when material -> immutable recovery position supersession -> reversal referral -> accounting/reconciliation verification",
    }
