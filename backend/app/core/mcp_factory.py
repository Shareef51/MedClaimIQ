from __future__ import annotations

from functools import lru_cache

from app.mcp.circuit import CircuitBreakerRegistry
from app.mcp.registry import build_default_registry
from app.mcp.tools import build_tool_handlers
from app.core.config import get_settings


@lru_cache(maxsize=1)
def build_mcp_registry():
    settings = get_settings()
    return build_default_registry(
        build_tool_handlers(), default_timeout_seconds=settings.mcp_tool_timeout_seconds,
        read_max_attempts=settings.mcp_read_max_attempts,
    )


@lru_cache(maxsize=1)
def build_mcp_circuit_breakers():
    settings = get_settings()
    return CircuitBreakerRegistry(
        failure_threshold=settings.mcp_circuit_failure_threshold,
        recovery_seconds=settings.mcp_circuit_recovery_seconds,
    )
