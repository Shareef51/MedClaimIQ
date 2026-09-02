import json
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.domain.realtime import EventEnvelope
from app.main import app
from app.observability.adapters import langsmith_contract, phoenix_contract
from app.observability.redaction import sanitize_attributes
from app.services.llmops import estimate_model_cost, llmops_model_contract


def test_phi_redaction_hashes_prompt_and_tokens():
    value=sanitize_attributes({"prompt":"patient name Alice","access_token":"secret","safe":"ok"})
    assert "prompt" not in value and len(value["prompt_sha256"])==64
    assert "access_token" not in value and len(value["access_token_sha256"])==64
    assert value["safe"]=="ok"


def test_model_cost_is_null_when_pricing_unconfigured():
    cost,version=estimate_model_cost(Settings(),"unknown-model",1000,100)
    assert cost is None and version=="unconfigured"


def test_model_cost_uses_explicit_versioned_pricing_only():
    s=Settings(llmops_model_pricing_json=json.dumps({"m":{"input_usd_per_million":2,"output_usd_per_million":4,"version":"provider-2026-08"}}))
    cost,version=estimate_model_cost(s,"m",1_000_000,500_000)
    assert cost==4.0 and version=="provider-2026-08"


def test_llmops_contract_is_phi_safe_and_multi_backend():
    c=llmops_model_contract(Settings())
    assert c["raw_content_export"] is False
    assert "LangGraph" in c["trace_path"] and "Kafka workers" in c["trace_path"]
    assert set(c["exporters"])=={"langsmith","phoenix","otlp"}


def test_langsmith_and_phoenix_adapters_do_not_export_raw_prompts():
    s=Settings(langsmith_enabled=True,langsmith_api_key="x",phoenix_enabled=True)
    assert langsmith_contract(s)["raw_prompts_exported"] is False
    assert phoenix_contract(s)["raw_prompts_exported"] is False
    assert str(phoenix_contract(s)["endpoint"]).endswith("/v1/traces")


def test_public_llmops_model_endpoint_and_trace_response_header():
    client=TestClient(app)
    r=client.get("/api/v1/llmops-model")
    assert r.status_code==200 and r.json()["raw_content_export"] is False
    h=client.get("/api/v1/health")
    assert h.status_code==200 and len(h.headers["x-trace-id"])>=16


def test_event_envelope_supports_w3c_context_fields():
    e=EventEnvelope(event_id="e",event_type="x",tenant_id="t",aggregate_type="claim",aggregate_id="c",occurred_at=datetime.now(timezone.utc),producer="test",traceparent="00-"+"a"*32+"-"+"b"*16+"-01",tracestate="vendor=v")
    assert e.traceparent.startswith("00-") and e.tracestate=="vendor=v"
