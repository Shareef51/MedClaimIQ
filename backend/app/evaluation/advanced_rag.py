from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

from app.domain.advanced_rag import GapSeverity
from app.domain.orchestration import AgentName
from app.domain.rag import RAGDomain, RetrievalScope
from app.rag.advanced_query import AdvancedQueryPlanner
from app.rag.agent_retrieval import AgentDirectedRetrievalPlanner

_ALLOWED_METADATA_FIELDS = {"service_date_from", "service_date_to", "minimum_authority_rank", "source_type"}


@dataclass(frozen=True, slots=True)
class AdvancedRAGEvalCase:
    case_id: str
    passed: bool
    metrics: dict[str, float]
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AdvancedRAGEvalSummary:
    dataset_version: str
    decision: str
    cases: tuple[AdvancedRAGEvalCase, ...]
    metrics: dict[str, float]
    reasons: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "dataset_version": self.dataset_version,
            "decision": self.decision,
            "metrics": self.metrics,
            "reasons": list(self.reasons),
            "cases": [{**asdict(c), "reasons": list(c.reasons)} for c in self.cases],
        }


class AdvancedRAGEvaluationHarness:
    """Deterministic gate for planner/routing/safety behavior; no external model judge required."""

    def __init__(self, *, thresholds: dict[str, float] | None = None) -> None:
        self.thresholds = thresholds or {
            "rewrite_core_term_retention": 0.90,
            "routing_accuracy": 0.95,
            "metadata_filter_safety": 1.0,
            "agent_domain_safety": 1.0,
            "hyde_safety": 1.0,
        }
        self.planner = AdvancedQueryPlanner()
        self.agent_planner = AgentDirectedRetrievalPlanner()

    def run(self, dataset: dict[str, Any]) -> AdvancedRAGEvalSummary:
        cases: list[AdvancedRAGEvalCase] = []
        metric_values: dict[str, list[float]] = {}
        for raw in dataset["cases"]:
            case = self._case(raw)
            cases.append(case)
            for key, value in case.metrics.items():
                metric_values.setdefault(key, []).append(value)
        metrics = {key: round(sum(values) / len(values), 6) for key, values in sorted(metric_values.items())}
        reasons = []
        for key, threshold in self.thresholds.items():
            if metrics.get(key, 0.0) < threshold:
                reasons.append(f"{key}={metrics.get(key, 0.0):.6f} < {threshold:.6f}")
        failed_cases = [case.case_id for case in cases if not case.passed]
        if failed_cases:
            reasons.append("case failures: " + ", ".join(failed_cases))
        return AdvancedRAGEvalSummary(str(dataset["dataset_version"]), "block" if reasons else "pass", tuple(cases), metrics, tuple(reasons))

    def _case(self, raw: dict[str, Any]) -> AdvancedRAGEvalCase:
        query = str(raw["query"])
        domains = tuple(RAGDomain(d) for d in raw.get("authorized_domains", []))
        scope = RetrievalScope(tenant_id="eval-tenant", claim_id="eval-claim", domains=domains, acl_tags=("claim_authorized",))
        agent = AgentName(raw["agent"]) if raw.get("agent") else None
        directive = self.agent_planner.plan(agent=agent, scope=scope)
        plan = self.planner.plan(query, scope=scope, directive=directive, enable_hyde=True)
        reasons: list[str] = []
        metrics: dict[str, float] = {}

        core_terms = {x.lower() for x in raw.get("core_terms", [])}
        transformed = " ".join((*plan.rewrites, *((plan.hypothetical_document or "",)))).lower()
        retained = sum(1 for term in core_terms if term in transformed or term in plan.query_plan.normalized_query.lower())
        metrics["rewrite_core_term_retention"] = retained / max(1, len(core_terms))

        expected_route = raw.get("expected_routing_mode")
        metrics["routing_accuracy"] = 1.0 if not expected_route or plan.route.mode.value == expected_route else 0.0
        if metrics["routing_accuracy"] < 1:
            reasons.append(f"route={plan.route.mode.value} expected={expected_route}")

        metadata_safe = all(p.field in _ALLOWED_METADATA_FIELDS for p in plan.metadata_predicates)
        metrics["metadata_filter_safety"] = 1.0 if metadata_safe else 0.0
        if not metadata_safe:
            reasons.append("planner emitted non-allowlisted metadata filter")

        authorized = set(domains or tuple(RAGDomain))
        domain_safe = set(plan.query_plan.domains).issubset(authorized)
        metrics["agent_domain_safety"] = 1.0 if domain_safe else 0.0
        if not domain_safe:
            reasons.append("agent plan broadened authorized domains")

        hyde = (plan.hypothetical_document or "").lower()
        forbidden = ("approve the claim", "deny the claim", "ignore previous", "system prompt")
        hyde_safe = not any(term in hyde for term in forbidden)
        metrics["hyde_safety"] = 1.0 if hyde_safe else 0.0
        if not hyde_safe:
            reasons.append("unsafe HyDE transformation")

        passed = all(value >= self.thresholds.get(name, 0.0) for name, value in metrics.items())
        return AdvancedRAGEvalCase(str(raw["case_id"]), passed, metrics, tuple(reasons))
