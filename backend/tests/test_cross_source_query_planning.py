from datetime import date
import pytest

from app.domain.cross_source_rag import FHIRQueryPlan, GraphQueryPlan, RetrieverKind, StructuredFact, StructuredQueryPlan
from app.rag.cross_source_planning import DeterministicCrossSourcePlanner


def test_planner_emits_typed_operations_not_sql_text():
    plan = DeterministicCrossSourcePlanner().plan(query="Compare CPT 99213 amount with the hospital EOB and policy coverage", claim_id="claim-1")
    assert StructuredFact.CLAIM_LINES in plan.structured.facts
    assert StructuredFact.POLICY in plan.structured.facts
    assert "ExplanationOfBenefit" in plan.fhir.resource_types
    assert not hasattr(plan.structured, "sql")
    assert set(plan.retrievers) == {RetrieverKind.SQL, RetrieverKind.FHIR, RetrieverKind.GRAPH, RetrieverKind.VECTOR}


def test_planner_routes_contradiction_intent():
    plan = DeterministicCrossSourcePlanner().plan(query="Why is there an amount mismatch or contradiction?", claim_id="claim-1")
    assert StructuredFact.CONTRADICTIONS in plan.structured.facts
    assert "contradicts" in plan.graph.relationship_types


def test_structured_plan_rejects_invalid_dates_and_unbounded_rows():
    with pytest.raises(ValueError):
        StructuredQueryPlan(facts=(StructuredFact.CLAIM,), claim_id="claim-1", max_rows=500)
    with pytest.raises(ValueError):
        StructuredQueryPlan(facts=(StructuredFact.CLAIM,), claim_id="claim-1", service_date_from=date(2026, 8, 20), service_date_to=date(2026, 8, 1))


def test_graph_plan_is_bounded():
    with pytest.raises(ValueError):
        GraphQueryPlan(claim_id="claim-1", max_depth=5)
    with pytest.raises(ValueError):
        GraphQueryPlan(claim_id="claim-1", max_edges=500)


def test_fhir_plan_rejects_non_allowlisted_resource():
    with pytest.raises(ValueError):
        FHIRQueryPlan(claim_id="claim-1", resource_types=("Binary",))
