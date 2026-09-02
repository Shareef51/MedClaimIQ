from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.mcp import MCPExecutionMode, MCPInvocationStatus, MCPRiskTier
from app.domain.orchestration import AgentName


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ClaimSummaryInput(_StrictModel):
    include_lines: bool = True


class ClaimSummaryOutput(_StrictModel):
    claim_id: str
    external_claim_ref: str
    status: str
    total_amount: str
    currency: str
    service_from: date
    service_to: date | None = None
    claim_lines: list[dict[str, Any]] = Field(default_factory=list)


class PolicyLookupInput(_StrictModel):
    policy_id: str | None = None


class PolicyLookupOutput(_StrictModel):
    policy_id: str
    policy_ref: str
    plan_name: str
    status: str
    effective_from: date
    effective_to: date | None = None
    policy_version: int
    source_system: str


class FHIRResourceReadInput(_StrictModel):
    resource_type: Literal["Patient", "Encounter", "Coverage", "Claim", "ExplanationOfBenefit", "DocumentReference", "Organization", "Practitioner"]
    logical_id: str | None = Field(default=None, max_length=256)
    version_id: str | None = Field(default=None, max_length=128)


class FHIRResourceReadOutput(_StrictModel):
    snapshot_id: str
    resource_type: str
    logical_id: str
    version_id: str
    content_sha256: str
    authoritative: bool
    resource: dict[str, Any]


class AuditContextInput(_StrictModel):
    limit: int = Field(default=20, ge=1, le=100)


class AuditContextOutput(_StrictModel):
    events: list[dict[str, Any]]


class RequestEvidenceInput(_StrictModel):
    evidence_types: list[str] = Field(min_length=1, max_length=10)
    reason: str = Field(min_length=5, max_length=500)
    recipient_role: Literal["patient", "provider", "hospital"]

    @field_validator("evidence_types")
    @classmethod
    def clean_types(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip().lower() for item in value if item.strip()]
        if not cleaned:
            raise ValueError("at least one evidence type is required")
        return list(dict.fromkeys(cleaned))


class RequestEvidenceOutput(_StrictModel):
    request_id: str
    claim_id: str
    status: str
    evidence_types: list[str]
    recipient_role: str


class NotificationInput(_StrictModel):
    channel: Literal["email", "sms", "portal"]
    recipient_ref: str = Field(min_length=3, max_length=160)
    template_key: str = Field(min_length=3, max_length=120)
    variables: dict[str, str] = Field(default_factory=dict)


class NotificationOutput(_StrictModel):
    notification_id: str
    status: str
    channel: str
    recipient_ref_hash: str
    provider_message_id: str | None = None


class MCPInvokeRequest(_StrictModel):
    mode: MCPExecutionMode = MCPExecutionMode.READ
    input: dict[str, Any] = Field(default_factory=dict)
    agent_name: AgentName | None = None
    workflow_id: str | None = None
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=160)
    approval_id: str | None = None


class MCPInvokeResponse(_StrictModel):
    invocation_id: str
    tool_name: str
    status: MCPInvocationStatus
    output: dict[str, Any]
    provenance: dict[str, Any]
    approval_id: str | None = None
    sanitized: bool = False
    attempts: int = 0


class MCPApprovalDecisionRequest(_StrictModel):
    decision: Literal["approve", "reject"]
    comment: str | None = Field(default=None, max_length=1000)


class MCPApprovalResponse(_StrictModel):
    approval_id: str
    status: str
    tool_name: str
    claim_id: str


class MCPToolDescription(_StrictModel):
    name: str
    version: str
    description: str
    risk_tier: MCPRiskTier
    required_permission: str
    allowed_agents: list[str]
    supports_dry_run: bool
    requires_human_approval: bool
    external_side_effect: bool


class MCPHealthResponse(_StrictModel):
    status: str
    registry_tools: int
    circuits: dict[str, str]

class MCPJSONRPCRequest(_StrictModel):
    jsonrpc: Literal["2.0"] = "2.0"
    id: str | int | None = None
    method: Literal["server/discover", "tools/list", "tools/call"]
    params: dict[str, Any] = Field(default_factory=dict)


class MCPJSONRPCResponse(_StrictModel):
    jsonrpc: Literal["2.0"] = "2.0"
    id: str | int | None = None
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None

class MCPInvocationTelemetryItem(_StrictModel):
    invocation_id: str
    tool_name: str
    tool_version: str
    risk_tier: str
    mode: str
    status: str
    agent_name: str | None = None
    input_sha256: str
    output_sha256: str | None = None
    sanitized: bool
    attempts: int
    error_code: str | None = None
    trace_id: str | None = None
    created_at: datetime
    completed_at: datetime | None = None
