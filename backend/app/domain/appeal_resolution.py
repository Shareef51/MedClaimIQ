from __future__ import annotations
from enum import StrEnum

class AppealDecisionPacketStatus(StrEnum):
    DRAFT="draft"; VALIDATED="validated"; LOCKED="locked"; PENDING_SECOND_REVIEW="pending_second_review"; SECOND_REVIEW_APPROVED="second_review_approved"; CLOSED="closed"; BLOCKED="blocked"
class AppealFinalOutcome(StrEnum): AFFIRM="affirm"; MODIFY="modify"; OVERTURN="overturn"
class AppealSecondReviewAction(StrEnum): APPROVE="approve"; REJECT="reject"

MATERIAL_FINANCIAL_CHANGE_ABS=100.0
MATERIAL_FINANCIAL_CHANGE_PCT=0.10

def appeal_resolution_contract()->dict[str,object]:
    return {
      "workflow":["immutable_reconsideration_snapshot","human_appeal_decision_packet","citation_and_completeness_validation","contradiction_resolution","packet_lock","dual_control_when_required","human_final_resolution","immutable_supersession_version","checkpoint_completion","human_released_reconsideration_notice","communication_delivery","sla_closure"],
      "blocking_rules":{"locked_snapshot_required":True,"citations_required":True,"material_contradictions_must_be_resolved":True,"open_missing_evidence_blocks":True,"recommendation_disagreement_requires_reason":True},
      "dual_control":{"overturn":True,"material_financial_change":True,"second_reviewer_must_differ":True,"original_adjudication_reviewer_excluded":True},
      "authority":{"llm_can_create_controlling_outcome":False,"langgraph_can_create_controlling_outcome":False,"rag_can_create_controlling_outcome":False,"mcp_can_create_controlling_outcome":False,"automation_can_create_controlling_outcome":False,"authorized_human_reviewers_required":True,"automated_financial_execution":False},
      "traceability":"original decision -> appeal evidence snapshot -> comparisons/RAG citations -> recommendation-only agent -> primary human packet -> independent second human when required -> final human resolution -> superseding decision history -> released notice -> delivery receipt",
    }
