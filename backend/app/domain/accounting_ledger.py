from __future__ import annotations
from enum import StrEnum

class AccountingPeriodStatus(StrEnum):
    OPEN="open"; CLOSING="closing"; CLOSED="closed"
class LedgerJournalStatus(StrEnum):
    POSTED="posted"; REVERSED="reversed"
class ReconciliationStatus(StrEnum):
    OPEN="open"; PARTIAL="partial"; RECONCILED="reconciled"; EXCEPTION="exception"; RETURNED="returned"
class AdjustmentType(StrEnum):
    ADJUSTMENT="adjustment"; RECOUPMENT="recoupment"
class AdjustmentStatus(StrEnum):
    PENDING_APPROVAL="pending_approval"; APPROVED="approved"; POSTED="posted"; REJECTED="rejected"

ACCOUNTING_AUTHORITY={
    "llm_can_post_journal":False,
    "langgraph_can_post_journal":False,
    "rag_can_post_journal":False,
    "mcp_can_post_journal":False,
    "background_worker_can_post_journal":False,
    "background_worker_can_close_period":False,
    "ai_can_authorize_adjustment_or_recoupment":False,
    "automatic_fund_movement":False,
    "human_finance_approval_required":True,
    "human_accounting_controller_close_required":True,
    "double_entry_required":True,
}

def accounting_ledger_contract()->dict[str,object]:
    return {
        "name":"production_financial_ledger_era_eft_reconciliation_accounting_close",
        "workflow":[
            "human_authorized_payment_intent","immutable_double_entry_journal","era_ingestion","eft_ingestion",
            "reference_and_amount_correlation","partial_multi_payment_reconciliation","returned_payment_reversal",
            "human_adjustment_recoupment_approval","provider_remittance_status","aging_queue","accounting_period_close",
            "immutable_journal_provenance","audit_and_sse"
        ],
        "authority":ACCOUNTING_AUTHORITY,
        "accounting_policy":{
            "balanced_journal_required":True,"closed_period_is_immutable":True,
            "period_close_requires_no_blocking_reconciliation":True,"segregation_of_duties":True,
            "era_eft_are_external_evidence_not_authority":True,
        },
    }
