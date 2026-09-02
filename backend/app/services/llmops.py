from __future__ import annotations

import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean
from uuid import uuid4

from app.domain.llmops import ModelPricing, SLOThresholds
from app.models.llmops import AISLOEventModel
from app.observability.adapters import langsmith_contract, phoenix_contract
from app.repositories.llmops import LLMOpsRepository

ROOT = Path(__file__).resolve().parents[3]


def load_llmops_policy() -> dict:
    return json.loads((ROOT / "config/llmops_policy.json").read_text())


def _p95(values: list[float]) -> float:
    if not values: return 0.0
    values = sorted(values); index = max(0, math.ceil(0.95 * len(values)) - 1); return float(values[index])




def estimate_model_cost(settings, model: str, input_tokens: int | None, output_tokens: int | None) -> tuple[float | None, str]:
    try:
        pricing = json.loads(settings.llmops_model_pricing_json or "{}")
    except json.JSONDecodeError:
        pricing = {}
    item = pricing.get(model) or {}
    version = str(item.get("version") or "unconfigured")
    try:
        inp = float(item["input_usd_per_million"]); out = float(item["output_usd_per_million"])
    except (KeyError, TypeError, ValueError):
        return None, version
    return ModelPricing(model=model, input_usd_per_million=inp, output_usd_per_million=out, version=version).estimate(input_tokens, output_tokens), version

def llmops_model_contract(settings) -> dict[str, object]:
    policy = load_llmops_policy()
    return {
        "telemetry_boundary": "PHI-safe OpenTelemetry plus authoritative application audit tables",
        "trace_path": ["FastAPI", "RAG", "FHIR", "LangGraph", "OpenAI", "MCP", "Kafka workers"],
        "raw_content_export": False,
        "correlation": ["trace_id", "span_id", "workflow_id", "retrieval_run_id", "evaluation_run_id"],
        "cost_accounting": "token ledger plus configurable model pricing; unknown pricing remains null rather than invented",
        "sampling": {"ratio": settings.otel_trace_sample_ratio, "parent_based": True, "safety_audit_records_are_unsampled": True},
        "slo_thresholds": policy["slos"],
        "exporters": {"langsmith": langsmith_contract(settings), "phoenix": phoenix_contract(settings), "otlp": bool(settings.otel_exporter_otlp_endpoint)},
    }


class LLMOpsService:
    def __init__(self, repository: LLMOpsRepository, settings) -> None:
        self.repository = repository; self.settings = settings; self.policy = load_llmops_policy()

    def summary(self, window_minutes: int = 60) -> dict:
        window_minutes = max(5, min(24 * 60, int(window_minutes)))
        since = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
        usages = self.repository.usage_since(since)
        agents = self.repository.agent_executions_since(since)
        retrievals = self.repository.retrieval_runs_since(since)
        mcp = self.repository.mcp_invocations_since(since)
        evals = self.repository.evaluation_runs_since(since)
        costs = [float(x.estimated_cost_usd) for x in usages if x.estimated_cost_usd is not None]
        model_latency = [float(x.latency_ms or 0) for x in usages if x.latency_ms is not None]
        agent_latency = [float(x.latency_ms or 0) for x in agents]
        retrieval_latency = [float(x.latency_ms or 0) for x in retrievals]
        agent_errors = sum(1 for x in agents if x.status != "succeeded")
        mcp_errors = sum(1 for x in mcp if getattr(x, "status", "") not in {"succeeded", "success", "completed", "dry_run", "approval_required"})
        model_counts: dict[str, int] = {}
        for item in usages: model_counts[item.model_name] = model_counts.get(item.model_name, 0) + 1
        return {
            "window_minutes": window_minutes,
            "model_calls": len(usages),
            "input_tokens": sum(x.input_tokens or 0 for x in usages),
            "output_tokens": sum(x.output_tokens or 0 for x in usages),
            "estimated_cost_usd": round(sum(costs), 6) if costs else None,
            "unpriced_model_calls": sum(1 for x in usages if x.estimated_cost_usd is None),
            "model_counts": model_counts,
            "model_latency_p95_ms": _p95(model_latency),
            "agent_executions": len(agents),
            "agent_error_rate": round(agent_errors / len(agents), 4) if agents else 0.0,
            "agent_latency_p95_ms": _p95(agent_latency),
            "retrieval_runs": len(retrievals),
            "retrieval_latency_p95_ms": _p95(retrieval_latency),
            "retrieval_no_evidence_rate": round(sum(1 for x in retrievals if x.no_evidence) / len(retrievals), 4) if retrievals else 0.0,
            "mcp_invocations": len(mcp),
            "mcp_error_rate": round(mcp_errors / len(mcp), 4) if mcp else 0.0,
            "evaluation_runs": len(evals),
            "evaluation_block_rate": round(sum(1 for x in evals if x.decision != "pass") / len(evals), 4) if evals else 0.0,
            "slo_events": [self._slo_dict(item) for item in self.repository.recent_slo_events(20)],
        }

    def evaluate_slos(self, window_minutes: int = 60) -> list[AISLOEventModel]:
        summary = self.summary(window_minutes)
        thresholds = self.policy["slos"]
        checks = [
            ("model_latency_p95_ms", summary["model_latency_p95_ms"], thresholds["model_latency_p95_ms"]),
            ("retrieval_latency_p95_ms", summary["retrieval_latency_p95_ms"], thresholds["retrieval_latency_p95_ms"]),
            ("agent_error_rate", summary["agent_error_rate"], thresholds["agent_error_rate"]),
            ("mcp_error_rate", summary["mcp_error_rate"], thresholds["mcp_error_rate"]),
        ]
        if summary["estimated_cost_usd"] is not None:
            checks.append(("daily_cost_usd", float(summary["estimated_cost_usd"]), thresholds["daily_cost_usd"]))
        created: list[AISLOEventModel] = []
        bucket=datetime.now(timezone.utc).replace(minute=0,second=0,microsecond=0)
        for kind, observed, threshold in checks:
            if float(observed) <= float(threshold): continue
            dedupe_key=f"{kind}:{window_minutes}:{bucket.isoformat()}"
            if self.repository.slo_by_dedupe(dedupe_key): continue
            row = AISLOEventModel(
                slo_event_id=f"aslo_{uuid4().hex}", tenant_id=self.repository.tenant_id,
                slo_kind=kind, dedupe_key=dedupe_key, severity="critical" if float(observed) > float(threshold) * 1.5 else "warning",
                observed_value=float(observed), threshold_value=float(threshold), window_minutes=window_minutes,
                trace_id=None, details={"source": "llmops_slo_evaluator", "bucket": bucket.isoformat()}, occurred_at=datetime.now(timezone.utc),
            )
            self.repository.add_slo_event(row); created.append(row)
        return created

    def trace_detail(self, trace_id: str) -> dict:
        raw = self.repository.trace_detail(trace_id)
        return {
            "trace_id": trace_id,
            "agent_executions": [{"agent": x.agent_name, "status": x.status, "latency_ms": x.latency_ms, "workflow_id": x.workflow_id} for x in raw["agent_executions"]],
            "workflow_path": [{"workflow_id":x.workflow_id,"sequence":x.sequence,"event_type":x.event_type,"actor_type":x.actor_type} for x in raw["workflow_events"]],
            "model_invocations": [{"agent":x.agent_name,"model":x.model_name,"prompt_key":x.prompt_key,"prompt_version":x.prompt_version,"prompt_sha256":x.prompt_sha256,"input_tokens":x.input_tokens,"output_tokens":x.output_tokens} for x in raw["model_invocations"]],
            "agent_tool_calls": [{"agent":x.agent_name,"tool":x.tool_name,"result_count":x.result_count,"input_sha256":x.input_sha256,"result_sha256":x.result_sha256} for x in raw["agent_tool_audits"]],
            "retrieval_runs": [{"run_id": x.retrieval_run_id, "strategy": x.strategy, "latency_ms": x.latency_ms, "confidence": x.confidence, "no_evidence": x.no_evidence} for x in raw["retrieval_runs"]],
            "retrieved_chunks": [{"run_id":x.retrieval_run_id,"chunk_id":x.chunk_id,"source_id":x.source_id,"rank":x.final_rank,"selected":x.selected,"rerank_score":x.rerank_score} for x in raw["retrieval_candidates"]],
            "mcp_tool_calls": [{"tool":x.tool_name,"status":x.status,"risk_tier":x.risk_tier,"attempts":x.attempts,"sanitized":x.sanitized} for x in raw["mcp_invocations"]],
            "evaluation_runs": [{"run_id": x.run_id, "decision": x.decision, "candidate": x.candidate_version} for x in raw["evaluation_runs"]],
            "usage": [{"model": x.model_name, "tokens": (x.input_tokens or 0) + (x.output_tokens or 0), "cost_usd": x.estimated_cost_usd, "prompt_version": x.prompt_version} for x in raw["usage"]],
        }

    @staticmethod
    def _slo_dict(x):
        return {"slo_event_id": x.slo_event_id, "slo_kind": x.slo_kind, "severity": x.severity, "observed_value": x.observed_value, "threshold_value": x.threshold_value, "occurred_at": x.occurred_at.isoformat()}
