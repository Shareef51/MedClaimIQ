from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from app.domain.access import Permission
from app.domain.mcp import MCPRiskTier, MCPToolSpec
from app.domain.orchestration import AgentName


@dataclass(frozen=True, slots=True)
class RegisteredMCPTool:
    spec: MCPToolSpec
    input_schema: type[BaseModel]
    output_schema: type[BaseModel]
    handler: Callable[[BaseModel, Any], BaseModel | dict[str, Any]]


class MCPToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, RegisteredMCPTool] = {}

    def register(self, tool: RegisteredMCPTool) -> None:
        if tool.spec.name in self._tools:
            raise ValueError(f"duplicate MCP tool: {tool.spec.name}")
        self._tools[tool.spec.name] = tool

    def get(self, name: str) -> RegisteredMCPTool:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise KeyError(f"unknown MCP tool: {name}") from exc

    def list(self) -> tuple[RegisteredMCPTool, ...]:
        return tuple(self._tools[name] for name in sorted(self._tools))

    def tools_for_agent(self, agent: AgentName) -> tuple[RegisteredMCPTool, ...]:
        return tuple(tool for tool in self.list() if agent in tool.spec.allowed_agents)


def build_default_registry(handlers: dict[str, Callable], *, default_timeout_seconds: float = 10.0, read_max_attempts: int = 2) -> MCPToolRegistry:
    # Lazy import avoids a circular dependency between schemas/registry/tool handlers.
    from app.schemas.mcp import (
        AuditContextInput, AuditContextOutput, ClaimSummaryInput, ClaimSummaryOutput,
        FHIRResourceReadInput, FHIRResourceReadOutput, NotificationInput, NotificationOutput,
        PolicyLookupInput, PolicyLookupOutput, RequestEvidenceInput, RequestEvidenceOutput,
    )

    registry = MCPToolRegistry()
    specs = (
        ("fhir.resource.read", "1.0.0", "Read a versioned FHIR snapshot bound to the claim.", MCPRiskTier.READ_ONLY,
         Permission.HOSPITAL_RECORD_READ, {AgentName.HOSPITAL_VERIFICATION, AgentName.ELIGIBILITY},
         FHIRResourceReadInput, FHIRResourceReadOutput, False, False),
        ("policy.lookup", "1.0.0", "Read the persisted policy bound to the claim.", MCPRiskTier.READ_ONLY,
         Permission.CLAIM_READ, {AgentName.POLICY, AgentName.ELIGIBILITY, AgentName.DENIAL_RISK},
         PolicyLookupInput, PolicyLookupOutput, False, False),
        ("claims.summary.read", "1.0.0", "Read a minimal deterministic claim summary.", MCPRiskTier.READ_ONLY,
         Permission.CLAIM_READ, {AgentName.INTAKE, AgentName.DUPLICATE_CLAIM, AgentName.DENIAL_RISK, AgentName.EVIDENCE_FUSION, AgentName.CRITIC, AgentName.DECISION_SUPPORT, AgentName.HUMAN_REVIEW_ROUTER},
         ClaimSummaryInput, ClaimSummaryOutput, False, False),
        ("audit.context.read", "1.0.0", "Read claim-scoped audit actions without raw secrets.", MCPRiskTier.READ_ONLY,
         Permission.AUDIT_READ, {AgentName.CRITIC, AgentName.HUMAN_REVIEW_ROUTER},
         AuditContextInput, AuditContextOutput, False, False),
        ("claim.request_evidence", "1.0.0", "Prepare or execute a missing-evidence request after human approval.", MCPRiskTier.CONTROLLED_WRITE,
         Permission.CLAIM_REQUEST_EVIDENCE, {AgentName.DECISION_SUPPORT, AgentName.HUMAN_REVIEW_ROUTER},
         RequestEvidenceInput, RequestEvidenceOutput, True, False),
        ("notification.claim_update", "1.0.0", "Prepare or send an external claim-status notification after human approval.", MCPRiskTier.HIGH_RISK_EXTERNAL,
         Permission.CLAIM_REQUEST_EVIDENCE, {AgentName.HUMAN_REVIEW_ROUTER},
         NotificationInput, NotificationOutput, True, True),
    )
    for name, version, description, risk, permission, agents, input_schema, output_schema, approval, external in specs:
        registry.register(RegisteredMCPTool(
            spec=MCPToolSpec(
                name=name, version=version, description=description, risk_tier=risk,
                required_permission=permission, allowed_agents=frozenset(agents), timeout_seconds=default_timeout_seconds,
                max_attempts=read_max_attempts if risk is MCPRiskTier.READ_ONLY else 1, idempotent=True,
                requires_human_approval=approval, supports_dry_run=approval,
                external_side_effect=external,
            ),
            input_schema=input_schema, output_schema=output_schema, handler=handlers[name],
        ))
    return registry
