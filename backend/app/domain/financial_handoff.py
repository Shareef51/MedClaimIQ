from __future__ import annotations
from enum import StrEnum

class FinancialPacketStatus(StrEnum):
    DRAFT="draft"; LOCKED="locked"; PENDING_AUTHORIZATION="pending_authorization"; AUTHORIZED="authorized"; HELD="held"; VOIDED="voided"
class PaymentIntentStatus(StrEnum):
    STAGED="staged"; READY="ready_for_handoff"; SUBMITTED="submitted"; ACCEPTED="accepted"; SETTLED="settled"; FAILED="failed"; RETURNED="returned"; VOID_PENDING="void_pending"; VOIDED="voided"; REISSUE_PENDING="reissue_pending"
class SettlementStatus(StrEnum):
    ACCEPTED="accepted"; SETTLED="settled"; FAILED="failed"; RETURNED="returned"; VOIDED="voided"
class FinancialTaskType(StrEnum):
    PACKET_AUTHORIZATION="packet_authorization"; PAYMENT_HANDOFF="payment_handoff"; SETTLEMENT_RECONCILIATION="settlement_reconciliation"; EXCEPTION_REVIEW="exception_review"; VOID_REISSUE="void_reissue"

FINANCIAL_AUTHORITY = {
    "llm_can_authorize_funds": False,
    "langgraph_can_authorize_funds": False,
    "rag_can_authorize_funds": False,
    "mcp_can_authorize_funds": False,
    "background_worker_can_authorize_funds": False,
    "adapter_can_authorize_funds": False,
    "authorized_human_finance_approver_required": True,
    "segregation_of_duties_required": True,
    "automatic_fund_movement": False,
}

def financial_handoff_contract()->dict[str,object]:
    return {
        "workflow":["resolve_controlling_human_decision","line_reconciliation","benefit_member_responsibility","immutable_financial_packet","remittance_artifacts","packet_lock","human_finance_authorization","payment_intent_staging","idempotent_financial_handoff","settlement_status_ingestion","reconciliation","human_void_reissue"],
        "controls":{"controlling_human_decision_required":True,"decision_hash_binding":True,"duplicate_payment_prevention":True,"fraud_payment_holds_block":True,"segregation_of_duties":True,"settlement_callbacks_cannot_authorize":True,"void_reissue_requires_human_approval":True},
        "authority":FINANCIAL_AUTHORITY,
        "x12_note":"835-style deterministic educational mapping; not a claim of X12 certification or trading-partner compliance",
        "traceability":"evidence -> locked human adjudication -> controlling decision history -> immutable financial packet -> human finance authorization -> staged instruction -> external acknowledgement/status -> settlement reconciliation",
    }
