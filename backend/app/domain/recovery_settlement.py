from __future__ import annotations

RECOVERY_SETTLEMENT_AUTHORITY={
    "ai_can_match_evidence":True,"ai_can_recommend":True,"ai_can_collect_funds":False,
    "langgraph_can_collect_funds":False,"rag_can_collect_funds":False,"mcp_can_collect_funds":False,
    "background_worker_can_create_bank_transaction":False,"background_worker_can_approve_accounting":False,
    "background_worker_can_authorize_payment":False,"background_worker_can_close_financial_recovery":False,
    "independent_human_financial_closeout_required":True,
}
EVIDENCE_TYPES=("bank_repayment","provider_remittance","recoupment_offset","refund_credit")
EVIDENCE_STATUSES=("pending_verification","verified","rejected")
EXCEPTION_CODES=("reference_mismatch","currency_mismatch","over_recovery","unresolved_balance","missing_ledger_correlation","accounting_period_unavailable")
CERTIFICATE_STATUSES=("prepared","certified","rejected")

def recovery_settlement_contract()->dict[str,object]:
    return {
      "name":"production_recovery_settlement_evidence_provider_repayment_verification_financial_closeout",
      "workflow":["release46_controlling_recovery_position","repayment_evidence_intake","human_bank_reference_verification","installment_matching","recoupment_offset_or_refund_credit_verification","recovery_ledger_correlation","settlement_exception_queue","completion_certificate","independent_human_financial_closeout","accounting_period_linkage","immutable_settlement_provenance","sse_operations"],
      "matching":{"multi_installment":True,"partial_settlement":True,"reference_verification":True,"currency_verification":True,"ledger_correlation_required_for_positive_closeout":True},
      "authority":RECOVERY_SETTLEMENT_AUTHORITY,
      "traceability":"final human recovery decision -> immutable recovery position -> external repayment/offset evidence -> human verification -> accounting journal correlation -> independent human closeout certificate",
    }
