from __future__ import annotations

from enum import StrEnum


class CommunicationChannel(StrEnum):
    EMAIL = "email"
    SMS = "sms"
    PORTAL = "portal"


class DispatchStatus(StrEnum):
    QUEUED = "queued"
    LEASED = "leased"
    SENT = "sent"
    DELIVERED = "delivered"
    RETRY_PENDING = "retry_pending"
    BOUNCED = "bounced"
    FAILED = "failed"
    DEAD_LETTERED = "dead_lettered"
    SUPPRESSED = "suppressed"


class ReceiptStatus(StrEnum):
    ACCEPTED = "accepted"
    DELIVERED = "delivered"
    BOUNCED = "bounced"
    FAILED = "failed"
    COMPLAINT = "complaint"


class ConsentStatus(StrEnum):
    OPTED_IN = "opted_in"
    OPTED_OUT = "opted_out"
    REQUIRED_ONLY = "required_only"


class TemplateStatus(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    RETIRED = "retired"


SUPPORTED_LOCALES = ("en", "es", "ar")


def communication_delivery_contract() -> dict[str, object]:
    return {
        "channels": [x.value for x in CommunicationChannel],
        "supported_locales": list(SUPPORTED_LOCALES),
        "workflow": [
            "locked_human_decision",
            "human_released_notice",
            "approved_template_version",
            "consent_and_destination_resolution",
            "encrypted_dispatch",
            "worker_lease",
            "provider_dispatch",
            "signed_webhook_receipt",
            "correspondence_reconciliation",
            "appeal_lifecycle",
        ],
        "controls": {
            "destination_encrypted_at_rest": True,
            "dispatch_idempotency": True,
            "worker_leases": True,
            "exponential_backoff": True,
            "signed_provider_receipts": True,
            "regulatory_deadlines": True,
            "template_approval_required": True,
            "retention_and_legal_hold": True,
            "audit_export_hash_manifest": True,
            "pdf_notice_rendering": True,
            "accessibility_ready_html_and_text": True,
        },
        "human_authority": {
            "communication_workers_can_adjudicate": False,
            "providers_can_adjudicate": False,
            "llm_can_issue_or_overturn": False,
            "langgraph_can_issue_or_overturn": False,
            "rag_can_issue_or_overturn": False,
            "mcp_can_issue_or_overturn": False,
            "automation_can_financially_adjudicate": False,
            "workers_may_deliver_only_human_released_notices": True,
        },
    }
