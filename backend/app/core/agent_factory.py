from __future__ import annotations

from sqlalchemy.orm import Session

from app.agents.model_client import OpenAIResponsesStructuredClient
from app.agents.specialists import build_specialist_registry
from app.core.ai_config_runtime import resolve_agent_runtime_configuration
from app.core.config import Settings
from app.orchestration.evidence_hydration import DatabaseEvidenceSnapshotProvider


def build_production_specialist_registry(session: Session, tenant_id: str, settings: Settings):
    provider = DatabaseEvidenceSnapshotProvider(session, tenant_id)
    client = OpenAIResponsesStructuredClient()
    runtime = resolve_agent_runtime_configuration(
        session=session, tenant_id=tenant_id, environment=settings.environment,
        config_key=settings.ai_config_bundle_key,
        default_model=settings.agent_model_name,
        default_fallback_model=settings.agent_fallback_model,
        default_prompt_version=settings.agent_prompt_version,
        enabled=settings.ai_config_registry_enabled,
        required=settings.ai_config_registry_required,
    )
    return build_specialist_registry(
        model_client=client,
        evidence_provider=provider,
        model=runtime.model,
        fallback_model=runtime.fallback_model,
        prompt_version=runtime.prompt_version,
        role_overrides=runtime.role_overrides,
    )
