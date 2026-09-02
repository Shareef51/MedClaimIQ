from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.repositories.ai_change_management import AIChangeManagementRepository


@dataclass(frozen=True, slots=True)
class AgentRuntimeConfiguration:
    snapshot_id: str | None
    version: str
    model: str
    fallback_model: str | None
    prompt_version: str
    role_overrides: dict[str, str]


def resolve_agent_runtime_configuration(*, session: Session, tenant_id: str, environment: str,
                                        config_key: str, default_model: str,
                                        default_fallback_model: str | None,
                                        default_prompt_version: str,
                                        enabled: bool = True, required: bool = False) -> AgentRuntimeConfiguration:
    fallback = AgentRuntimeConfiguration(
        snapshot_id=None, version="settings-fallback", model=default_model,
        fallback_model=default_fallback_model, prompt_version=default_prompt_version,
        role_overrides={},
    )
    if not enabled:
        return fallback
    try:
        repo = AIChangeManagementRepository(session, tenant_id)
        assignment = repo.assignment(environment, config_key)
        if assignment is None:
            if required:
                raise RuntimeError(f"required AI configuration assignment is missing: {environment}/{config_key}")
            return fallback
        snapshot = repo.snapshot(assignment.snapshot_id)
        if snapshot is None:
            raise RuntimeError("AI configuration assignment references a missing snapshot")
        payload: dict[str, Any] = dict(snapshot.payload)
        return AgentRuntimeConfiguration(
            snapshot_id=snapshot.snapshot_id,
            version=snapshot.version,
            model=str(payload.get("model", default_model)),
            fallback_model=payload.get("fallback_model", default_fallback_model),
            prompt_version=str(payload.get("prompt_version", snapshot.version)),
            role_overrides={str(k): str(v) for k, v in dict(payload.get("role_overrides", {})).items()},
        )
    except SQLAlchemyError:
        if required:
            raise
        return fallback
