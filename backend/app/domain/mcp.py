from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from app.domain.access import Permission
from app.domain.orchestration import AgentName


class MCPRiskTier(StrEnum):
    READ_ONLY = "read_only"
    CONTROLLED_WRITE = "controlled_write"
    HIGH_RISK_EXTERNAL = "high_risk_external"


class MCPExecutionMode(StrEnum):
    READ = "read"
    DRY_RUN = "dry_run"
    EXECUTE = "execute"


class MCPInvocationStatus(StrEnum):
    SUCCEEDED = "succeeded"
    DRY_RUN = "dry_run"
    APPROVAL_REQUIRED = "approval_required"
    FAILED = "failed"
    DENIED = "denied"


class MCPApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CONSUMED = "consumed"
    EXPIRED = "expired"


class MCPCircuitState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass(frozen=True, slots=True)
class MCPToolSpec:
    name: str
    version: str
    description: str
    risk_tier: MCPRiskTier
    required_permission: Permission
    allowed_agents: frozenset[AgentName]
    timeout_seconds: float
    max_attempts: int
    idempotent: bool
    requires_human_approval: bool
    supports_dry_run: bool
    external_side_effect: bool


@dataclass(frozen=True, slots=True)
class MCPInvocationContext:
    tenant_id: str
    claim_id: str
    actor_type: str
    actor_id: str
    actor_role: str
    actor_permissions: frozenset[Permission]
    workflow_id: str | None = None
    agent_name: AgentName | None = None
    trace_id: str | None = None


@dataclass(frozen=True, slots=True)
class MCPToolResult:
    status: MCPInvocationStatus
    tool_name: str
    invocation_id: str
    output: dict[str, Any] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)
    approval_id: str | None = None
    sanitized: bool = False
    attempts: int = 0


class MCPPolicyError(RuntimeError):
    pass


class MCPToolExecutionError(RuntimeError):
    def __init__(self, message: str, *, retryable: bool = False, code: str = "tool_execution_error") -> None:
        super().__init__(message)
        self.retryable = retryable
        self.code = code
