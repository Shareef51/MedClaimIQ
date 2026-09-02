from __future__ import annotations

from app.agents.prompts import build_prompt_registry
from app.agents.structured import PROHIBITED_STRUCTURED_FIELDS
from app.domain.orchestration import AgentName


def specialist_agent_model_contract() -> dict[str, object]:
    prompts = build_prompt_registry()
    return {
        "agents": [agent.value for agent in AgentName],
        "prompt_versioning": {
            "versioned_per_agent": True,
            "prompt_keys": {agent.value: spec.prompt_key for agent, spec in prompts.items()},
            "current_version": "1.0.0",
            "prompt_hashing": "SHA-256",
        },
        "structured_outputs": {
            "provider": "OpenAI Responses API adapter",
            "strict_json_schema": True,
            "schema": "SpecialistAgentOutput",
            "prohibited_fields": sorted(PROHIBITED_STRUCTURED_FIELDS),
        },
        "evidence_boundary": {
            "immutable_pack_binding": True,
            "unknown_evidence_key_rejected": True,
            "material_finding_requires_citation": True,
            "retrieved_content_is_untrusted_data": True,
        },
        "tool_policy": {
            "allowlist": ["evidence.list", "evidence.get", "evidence.search", "contradiction.list"],
            "network_tools": False,
            "database_mutation_tools": False,
            "claim_lifecycle_tools": False,
            "tenant_switch_tools": False,
        },
        "confidence_contracts": {
            "range": [0.0, 1.0],
            "supported_findings_minimum": "agent-specific >= 0.55/0.60",
            "below_threshold": "contract violation or insufficient-evidence finding",
        },
        "retry_fallback": {
            "transient_model_errors": "one schema-compatible fallback model attempt, then bounded orchestration RetryPolicy",
            "fallback_model": "gpt-5.6-luna",
            "contract_violations": "non-retryable",
            "fallback": "human review / insufficient evidence; never fabricate",
        },
        "safety_boundaries": [
            "agents cannot finalize claim approval or denial",
            "decision-support recommendations are advisory and force human review",
            "agents cannot mutate tenant, claim lifecycle, authorization, or authoritative evidence graph",
            "agents cannot execute arbitrary SQL, network, filesystem, or payment actions",
        ],
    }
