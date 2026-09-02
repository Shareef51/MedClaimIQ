from __future__ import annotations

from app.core.mcp_factory import build_mcp_registry


def mcp_model_contract() -> dict[str, object]:
    registry = build_mcp_registry()
    return {
        "policy_id": "medclaimiq.mcp.v1",
        "deny_by_default": True,
        "scope": {
            "tenant": "server_resolved",
            "claim": "server_authorized",
            "agent_allowlists": "registry_enforced",
            "client_supplied_scope": False,
        },
        "risk_tiers": ["read_only", "controlled_write", "high_risk_external"],
        "controls": [
            "typed_input_output_schemas", "rbac_abac", "per_agent_allowlists",
            "dry_run", "human_approval", "idempotency", "bounded_retry",
            "circuit_breaker", "output_sanitization", "prompt_injection_screening",
            "provenance", "immutable_audit", "tenant_rls",
        ],
        "tools": [
            {
                "name": tool.spec.name,
                "version": tool.spec.version,
                "risk_tier": tool.spec.risk_tier.value,
                "required_permission": tool.spec.required_permission.value,
                "allowed_agents": sorted(agent.value for agent in tool.spec.allowed_agents),
                "supports_dry_run": tool.spec.supports_dry_run,
                "requires_human_approval": tool.spec.requires_human_approval,
                "external_side_effect": tool.spec.external_side_effect,
            }
            for tool in registry.list()
        ],
    }
