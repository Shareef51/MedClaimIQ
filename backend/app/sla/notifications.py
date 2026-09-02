from __future__ import annotations

from app.core.mcp_factory import build_mcp_circuit_breakers, build_mcp_registry
from app.domain.access import Permission
from app.domain.mcp import MCPExecutionMode, MCPInvocationContext, MCPInvocationStatus
from app.mcp.gateway import MCPGateway
from app.models.sla import SLATimerModel


class SLAMCPNotificationBridge:
    """Creates approval-gated MCP notification requests for SLA breaches.

    SLA automation never bypasses the MCP human-approval policy. The first invocation
    intentionally returns APPROVAL_REQUIRED; a human can approve through the existing
    MCP approval API before a later execution request is allowed.
    """

    def __init__(self, session, tenant_id: str, approval_ttl_minutes: int = 30) -> None:
        self.session = session
        self.tenant_id = tenant_id
        self.gateway = MCPGateway(
            session=session, tenant_id=tenant_id, registry=build_mcp_registry(),
            circuit_breakers=build_mcp_circuit_breakers(), approval_ttl_minutes=approval_ttl_minutes,
        )

    @staticmethod
    def payload(timer: SLATimerModel) -> dict:
        return {
            "channel": "portal",
            "recipient_ref": f"tenant-review-queue:{timer.tenant_id}",
            "template_key": "sla.breach",
            "variables": {
                "timer_id": timer.timer_id,
                "timer_type": timer.timer_type,
                "due_at": timer.due_at.isoformat(),
            },
        }

    def request_breach_notification(self, timer: SLATimerModel):
        context = MCPInvocationContext(
            tenant_id=timer.tenant_id, claim_id=timer.claim_id,
            actor_type="system_service", actor_id="sla-engine", actor_role="system_service",
            actor_permissions=frozenset({Permission.CLAIM_REQUEST_EVIDENCE}),
            trace_id=timer.trace_id,
        )
        result = self.gateway.invoke(
            tool_name="notification.claim_update", raw_input=self.payload(timer), context=context,
            mode=MCPExecutionMode.EXECUTE, idempotency_key=f"sla-notify-request:{timer.timer_id}",
        )
        if result.status not in {MCPInvocationStatus.APPROVAL_REQUIRED, MCPInvocationStatus.SUCCEEDED}:
            raise RuntimeError(f"MCP notification request failed: {result.status.value}")
        return result
