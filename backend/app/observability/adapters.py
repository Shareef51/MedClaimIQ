from __future__ import annotations


def langsmith_contract(settings) -> dict[str, object]:
    return {
        "enabled": bool(settings.langsmith_enabled),
        "transport": "OpenTelemetry OTLP/HTTP",
        "endpoint": settings.langsmith_otel_endpoint,
        "project": settings.langsmith_project,
        "raw_prompts_exported": False,
        "api_key_configured": bool(settings.langsmith_api_key),
        "mode": "otel",
    }


def phoenix_contract(settings) -> dict[str, object]:
    endpoint = settings.phoenix_collector_endpoint.rstrip("/") if settings.phoenix_collector_endpoint else None
    return {
        "enabled": bool(settings.phoenix_enabled),
        "transport": "OpenTelemetry OTLP/HTTP",
        "endpoint": f"{endpoint}/v1/traces" if endpoint and not endpoint.endswith("/v1/traces") else endpoint,
        "project": settings.phoenix_project,
        "raw_prompts_exported": False,
        "api_key_configured": bool(settings.phoenix_api_key),
    }
