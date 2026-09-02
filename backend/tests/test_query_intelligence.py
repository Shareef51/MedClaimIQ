from datetime import date

from app.domain.rag import RAGDomain
from app.rag.query_intelligence import DeterministicQueryPlanner


def test_query_planner_routes_cross_domain_and_extracts_codes_dates():
    plan = DeterministicQueryPlanner().plan(
        "Compare CPT 99213 invoice charges and policy coverage on 2026-08-10"
    )
    assert RAGDomain.CODING in plan.domains
    assert RAGDomain.INVOICE in plan.domains
    assert RAGDomain.POLICY in plan.domains
    assert "99213" in plan.exact_terms
    assert plan.service_date_from == date(2026, 8, 10)
    assert plan.service_date_to == date(2026, 8, 10)
    assert len(plan.subqueries) >= 2


def test_query_planner_respects_explicit_domain_allowlist():
    plan = DeterministicQueryPlanner().plan(
        "invoice and policy coverage",
        requested_domains=(RAGDomain.POLICY,),
    )
    assert plan.domains == (RAGDomain.POLICY,)
