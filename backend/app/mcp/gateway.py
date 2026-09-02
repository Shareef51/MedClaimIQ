from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from app.domain.mcp import (
    MCPApprovalStatus, MCPExecutionMode, MCPInvocationContext, MCPInvocationStatus,
    MCPPolicyError, MCPRiskTier, MCPToolExecutionError, MCPToolResult,
)
from app.mcp.circuit import CircuitBreakerRegistry
from app.mcp.registry import MCPToolRegistry
from app.mcp.sanitization import sanitize_tool_output
from app.observability.metrics import record_operation
from app.mcp.tools import MCPToolRuntime
from app.models.mcp import MCPApprovalRequestModel, MCPToolHealthEventModel, MCPToolInvocationModel
from app.repositories.mcp import MCPRepository


def _hash_payload(payload: dict[str, Any]) -> str:
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


class MCPGateway:
    """Deny-by-default MCP/tool gateway.

    The gateway owns policy, schemas, approvals, idempotency, circuit breaking, sanitization and audit.
    Tool handlers never decide their own authorization scope.
    """

    def __init__(
        self, *, session: Session, tenant_id: str, registry: MCPToolRegistry,
        circuit_breakers: CircuitBreakerRegistry | None = None,
        approval_ttl_minutes: int = 30,
    ) -> None:
        self.session = session
        self.tenant_id = tenant_id
        self.registry = registry
        self.repo = MCPRepository(session, tenant_id)
        self.circuits = circuit_breakers or CircuitBreakerRegistry()
        self.approval_ttl_minutes = max(1, approval_ttl_minutes)

    def invoke(
        self, *, tool_name: str, raw_input: dict[str, Any], context: MCPInvocationContext,
        mode: MCPExecutionMode, idempotency_key: str, approval_id: str | None = None,
    ) -> MCPToolResult:
        if context.tenant_id != self.tenant_id:
            raise MCPPolicyError("gateway tenant context mismatch")
        if not idempotency_key or len(idempotency_key) < 8:
            raise MCPPolicyError("idempotency key is required")
        tool = self.registry.get(tool_name)
        spec = tool.spec
        if spec.required_permission not in context.actor_permissions:
            raise MCPPolicyError(f"missing required permission: {spec.required_permission.value}")
        if context.agent_name is not None and context.agent_name not in spec.allowed_agents:
            raise MCPPolicyError(f"agent {context.agent_name.value} is not allowed to invoke {tool_name}")
        if context.agent_name is not None and not context.workflow_id:
            raise MCPPolicyError("agent tool invocation requires workflow binding")
        if spec.risk_tier is MCPRiskTier.READ_ONLY and mode is not MCPExecutionMode.READ:
            raise MCPPolicyError("read-only tool requires read mode")
        if spec.risk_tier is not MCPRiskTier.READ_ONLY and mode is MCPExecutionMode.READ:
            raise MCPPolicyError("write/external tool requires dry_run or execute mode")
        if mode is MCPExecutionMode.DRY_RUN and not spec.supports_dry_run:
            raise MCPPolicyError("tool does not support dry-run mode")

        try:
            parsed = tool.input_schema.model_validate(raw_input)
        except ValidationError as exc:
            raise MCPPolicyError("tool input failed schema validation") from exc
        input_payload = parsed.model_dump(mode="json")
        input_sha = _hash_payload(input_payload)

        replay = self.repo.invocation_by_idempotency(idempotency_key)
        if replay is not None:
            if replay.claim_id != context.claim_id or replay.tool_name != tool_name or replay.input_sha256 != input_sha:
                raise MCPPolicyError("idempotency key is already bound to a different tool request")
            return MCPToolResult(
                status=MCPInvocationStatus(replay.status), tool_name=tool_name,
                invocation_id=replay.invocation_id, output=dict(replay.output_payload or {}),
                provenance=dict(replay.provenance or {}), approval_id=replay.approval_id,
                sanitized=replay.sanitized, attempts=replay.attempts,
            )

        if mode is MCPExecutionMode.EXECUTE and spec.requires_human_approval:
            approval = self._validate_or_create_approval(
                spec=spec, context=context, input_payload=input_payload, input_sha=input_sha,
                approval_id=approval_id,
            )
            if approval.status != MCPApprovalStatus.APPROVED.value:
                return self._persist_terminal(
                    tool=tool, context=context, mode=mode, idempotency_key=idempotency_key,
                    input_sha=input_sha, status=MCPInvocationStatus.APPROVAL_REQUIRED,
                    output={}, provenance={"policy": "human_approval_required"}, approval_id=approval.approval_id,
                    attempts=0, sanitized=False,
                )
        else:
            approval = None

        self.circuits.before_call(tool_name)
        start = time.perf_counter()
        attempts = 0
        last_exc: Exception | None = None
        result_model: BaseModel | dict[str, Any] | None = None
        for attempt in range(1, spec.max_attempts + 1):
            attempts = attempt
            try:
                runtime = MCPToolRuntime(
                    session=self.session, tenant_id=context.tenant_id, claim_id=context.claim_id,
                    actor_type=context.actor_type, actor_id=context.actor_id, mode=mode.value,
                    idempotency_key=idempotency_key, trace_id=context.trace_id,
                )
                result_model = tool.handler(parsed, runtime)
                elapsed = time.perf_counter() - start
                if elapsed > spec.timeout_seconds:
                    raise MCPToolExecutionError("tool execution exceeded timeout", retryable=True, code="tool_timeout")
                self.circuits.success(tool_name)
                break
            except MCPToolExecutionError as exc:
                last_exc = exc
                self.circuits.failure(tool_name)
                if not exc.retryable or attempt >= spec.max_attempts:
                    break
            except (TimeoutError, ConnectionError) as exc:
                last_exc = MCPToolExecutionError(str(exc), retryable=True, code="tool_transient_error")
                self.circuits.failure(tool_name)
                if attempt >= spec.max_attempts:
                    break
            except Exception as exc:
                last_exc = MCPToolExecutionError(str(exc), retryable=False, code="tool_handler_error")
                self.circuits.failure(tool_name)
                break

        latency_ms = int((time.perf_counter() - start) * 1000)
        if result_model is None:
            assert last_exc is not None
            self._health(context, tool_name, "failed", latency_ms, getattr(last_exc, "code", "tool_error"))
            return self._persist_terminal(
                tool=tool, context=context, mode=mode, idempotency_key=idempotency_key,
                input_sha=input_sha, status=MCPInvocationStatus.FAILED, output={},
                provenance={"circuit_state": self.circuits.state(tool_name).value},
                approval_id=approval.approval_id if approval else None, attempts=attempts, sanitized=False,
                error=last_exc,
            )

        try:
            if isinstance(result_model, BaseModel):
                validated = tool.output_schema.model_validate(result_model.model_dump())
            else:
                validated = tool.output_schema.model_validate(result_model)
        except ValidationError as exc:
            self.circuits.failure(tool_name)
            self._health(context, tool_name, "failed", latency_ms, "tool_output_schema_violation")
            return self._persist_terminal(
                tool=tool, context=context, mode=mode, idempotency_key=idempotency_key,
                input_sha=input_sha, status=MCPInvocationStatus.FAILED, output={},
                provenance={"circuit_state": self.circuits.state(tool_name).value},
                approval_id=approval.approval_id if approval else None, attempts=attempts, sanitized=False,
                error=MCPToolExecutionError("tool output failed schema validation", retryable=False, code="tool_output_schema_violation"),
            )
        report = sanitize_tool_output(validated.model_dump(mode="json"))
        provenance = {
            "tool_version": spec.version, "risk_tier": spec.risk_tier.value,
            "external_side_effect": spec.external_side_effect,
            "input_sha256": input_sha, "output_sha256": report.output_sha256,
            "redacted_keys": list(report.redacted_keys), "injection_paths": list(report.injection_paths),
            "circuit_state": self.circuits.state(tool_name).value,
            "trace_id": context.trace_id,
        }
        status = MCPInvocationStatus.DRY_RUN if mode is MCPExecutionMode.DRY_RUN else MCPInvocationStatus.SUCCEEDED
        self._health(context, tool_name, "success", latency_ms, None)
        persisted = self._persist_terminal(
            tool=tool, context=context, mode=mode, idempotency_key=idempotency_key,
            input_sha=input_sha, status=status, output=dict(report.value), provenance=provenance,
            approval_id=approval.approval_id if approval else None, attempts=attempts, sanitized=report.sanitized,
        )
        if approval is not None and mode is MCPExecutionMode.EXECUTE:
            approval.status = MCPApprovalStatus.CONSUMED.value
            approval.consumed_at = datetime.now(timezone.utc)
        return persisted

    def _validate_or_create_approval(self, *, spec, context, input_payload, input_sha, approval_id):
        now = datetime.now(timezone.utc)
        if approval_id:
            approval = self.repo.get_approval(approval_id, for_update=True)
            if approval is None:
                raise MCPPolicyError("approval request was not found")
            if approval.claim_id != context.claim_id or approval.tool_name != spec.name or approval.input_sha256 != input_sha:
                raise MCPPolicyError("approval scope or input hash mismatch")
            if _aware(approval.expires_at) <= now:
                approval.status = MCPApprovalStatus.EXPIRED.value
                raise MCPPolicyError("approval request expired")
            if approval.status != MCPApprovalStatus.APPROVED.value:
                raise MCPPolicyError("approval request is not approved")
            return approval
        model = MCPApprovalRequestModel(
            approval_id=f"mcpapr_{uuid4().hex}", tenant_id=context.tenant_id, claim_id=context.claim_id,
            workflow_id=context.workflow_id, requested_by_actor_type=context.actor_type,
            requested_by_actor_id=context.actor_id, agent_name=context.agent_name.value if context.agent_name else None,
            tool_name=spec.name, tool_version=spec.version, input_sha256=input_sha,
            status=MCPApprovalStatus.PENDING.value, expires_at=now + timedelta(minutes=self.approval_ttl_minutes),
            created_at=now,
        )
        return self.repo.add_approval(model)

    def decide_approval(self, *, approval_id: str, reviewer_user_id: str, decision: str, comment: str | None) -> MCPApprovalRequestModel:
        approval = self.repo.get_approval(approval_id, for_update=True)
        if approval is None:
            raise MCPPolicyError("approval request was not found")
        if approval.status != MCPApprovalStatus.PENDING.value:
            raise MCPPolicyError("approval request is not pending")
        now = datetime.now(timezone.utc)
        if _aware(approval.expires_at) <= now:
            approval.status = MCPApprovalStatus.EXPIRED.value
            raise MCPPolicyError("approval request expired")
        approval.status = MCPApprovalStatus.APPROVED.value if decision == "approve" else MCPApprovalStatus.REJECTED.value
        approval.decided_by_user_id = reviewer_user_id
        approval.decision_comment_sha256 = sha256((comment or "").encode()).hexdigest() if comment else None
        approval.decided_at = now
        self.session.flush()
        return approval

    def _persist_terminal(self, *, tool, context, mode, idempotency_key, input_sha, status, output, provenance,
                          approval_id, attempts, sanitized, error: Exception | None = None) -> MCPToolResult:
        now = datetime.now(timezone.utc)
        output_sha = _hash_payload(output) if output else None
        model = MCPToolInvocationModel(
            invocation_id=f"mcpinv_{uuid4().hex}", tenant_id=context.tenant_id, claim_id=context.claim_id,
            workflow_id=context.workflow_id, actor_type=context.actor_type, actor_id=context.actor_id,
            agent_name=context.agent_name.value if context.agent_name else None, tool_name=tool.spec.name,
            tool_version=tool.spec.version, risk_tier=tool.spec.risk_tier.value, mode=mode.value,
            status=status.value, idempotency_key=idempotency_key, approval_id=approval_id,
            input_sha256=input_sha, output_sha256=output_sha, output_payload=output,
            sanitized=sanitized, attempts=attempts,
            error_code=getattr(error, "code", None) if error else None,
            error_sha256=sha256(str(error).encode()).hexdigest() if error else None,
            provenance=provenance, trace_id=context.trace_id, created_at=now, completed_at=now,
        )
        self.repo.add_invocation(model)
        return MCPToolResult(
            status=status, tool_name=tool.spec.name, invocation_id=model.invocation_id,
            output=output, provenance=provenance, approval_id=approval_id,
            sanitized=sanitized, attempts=attempts,
        )

    def _health(self, context: MCPInvocationContext, tool_name: str, outcome: str, latency_ms: int, error_code: str | None) -> None:
        record_operation(operation="mcp.tool",latency_ms=latency_ms,status=outcome,attributes={"tool":tool_name,"error_code":error_code or ""})
        self.repo.add_health_event(MCPToolHealthEventModel(
            health_event_id=f"mcphealth_{uuid4().hex}", tenant_id=context.tenant_id, tool_name=tool_name,
            circuit_state=self.circuits.state(tool_name).value, outcome=outcome, latency_ms=latency_ms,
            error_code=error_code, trace_id=context.trace_id, occurred_at=datetime.now(timezone.utc),
        ))
