from __future__ import annotations
import json
from pathlib import Path
from app.repositories.performance_resilience import PerformanceResilienceRepository

ROOT = Path(__file__).resolve().parents[3]


def load_performance_policy() -> dict:
    return json.loads((ROOT / "config/performance_resilience_policy.json").read_text())


def performance_resilience_model_contract() -> dict:
    p = load_performance_policy()
    return {
        "quality_model": "measured-load-plus-failure-injection-with-release-regression-gates",
        "latency_budgets_ms": p["latency_budgets_ms"],
        "error_budgets": p["error_budgets"],
        "throughput_targets": p["throughput_targets"],
        "datastore_budgets_ms": p["datastore_budgets_ms"],
        "worker_backpressure": p["worker_backpressure"],
        "autoscaling": p["autoscaling"],
        "resilience": p["resilience"],
        "regression": p["regression"],
        "chaos": p["chaos"],
        "tools": {
            "k6": "2.x load/SSE/API suites",
            "locust": "2.46.x stateful reviewer/provider journeys",
            "chaos_mesh": "2.8.x Kubernetes failure injection",
        },
        "safety": {
            "synthetic_data_only": True,
            "production_chaos_requires_human_approval": True,
            "authorization_or_data_integrity_failure_aborts_experiment": True,
        },
    }


class PerformanceResilienceService:
    def __init__(self, repo: PerformanceResilienceRepository):
        self.repo = repo

    def history(self, limit: int = 50) -> dict:
        runs = self.repo.runs(limit)
        experiments = self.repo.experiments(limit)
        capacity = self.repo.capacity(min(limit, 20))
        return {
            "runs": [
                {
                    "run_id": x.run_id, "suite_name": x.suite_name, "candidate_version": x.candidate_version,
                    "environment": x.environment, "status": x.status, "decision": x.decision,
                    "started_at": x.started_at, "completed_at": x.completed_at,
                } for x in runs
            ],
            "experiments": [
                {
                    "experiment_id": x.experiment_id, "name": x.experiment_name,
                    "dependency": x.dependency, "failure_mode": x.failure_mode, "status": x.status,
                    "steady_state_before": x.steady_state_before, "steady_state_after": x.steady_state_after,
                    "authorization_boundary_preserved": x.authorization_boundary_preserved,
                    "data_integrity_preserved": x.data_integrity_preserved, "recovery_seconds": x.recovery_seconds,
                } for x in experiments
            ],
            "capacity": [
                {
                    "snapshot_id": x.snapshot_id, "environment": x.environment, "api_replicas": x.api_replicas,
                    "worker_replicas": x.worker_replicas, "concurrent_users": x.concurrent_users,
                    "sustained_rps": x.sustained_rps, "sse_connections": x.sse_connections,
                    "worker_events_per_second": x.worker_events_per_second, "headroom_fraction": x.headroom_fraction,
                    "model_version": x.model_version,
                } for x in capacity
            ],
        }
