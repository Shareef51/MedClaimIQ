from __future__ import annotations

REGULATORY_EXAMINATION_AUTHORITY = {
    "ai_can_approve_examination_response": False,
    "langgraph_can_approve_examination_response": False,
    "rag_can_approve_examination_response": False,
    "mcp_can_approve_examination_response": False,
    "worker_can_approve_examination_response": False,
    "worker_can_represent_human_regulatory_authority": False,
    "worker_can_alter_financial_or_accounting_records": False,
    "worker_can_authorize_payments": False,
    "worker_can_collect_funds": False,
    "worker_can_move_money": False,
    "human_maker_checker_response_governance_required": True,
    "ai_assistance_is_draft_and_recommendation_only": True,
}

def regulatory_examination_contract() -> dict[str, object]:
    return {
        "name": "production_regulatory_examination_inquiry_response_supervisory_evidence_management",
        "workflow": [
            "certified_filing_and_supervisory_reconciliation",
            "regulator_examination_or_inquiry_case",
            "document_request_and_deadline",
            "immutable_examination_evidence_pack",
            "cited_financial_accounting_and_rag_retrieval",
            "ai_assisted_response_draft",
            "human_maker_review",
            "independent_human_checker_approval",
            "secure_regulator_correspondence_delivery",
            "supplemental_submission_reference",
            "examination_findings_and_remediation_commitments",
            "follow_up_deadline_and_supervisory_escalation",
            "immutable_response_version_chain",
            "human_examination_closure",
        ],
        "authority": REGULATORY_EXAMINATION_AUTHORITY,
        "policy": {
            "response_approval_is_human_only": True,
            "maker_checker_separation_required": True,
            "cited_evidence_required": True,
            "open_material_findings_block_closure": True,
            "open_document_requests_block_closure": True,
            "financial_and_accounting_sources_are_read_only": True,
            "automation_never_represents_regulatory_authority": True,
        },
    }
