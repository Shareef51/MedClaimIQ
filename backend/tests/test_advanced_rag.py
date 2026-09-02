from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from app.domain.advanced_rag import Answerability, RoutingMode
from app.domain.orchestration import AgentName
from app.domain.rag import QueryPlan, RAGDomain, RetrievalAssessment, RetrievalHit, RetrievalScope, RetrievalStrategy
from app.rag.advanced_query import AdvancedQueryPlanner
from app.rag.agent_retrieval import AgentDirectedRetrievalPlanner
from app.rag.citation_enforcement import CitationEnforcer
from app.rag.knowledge_gap import KnowledgeGapDetector
from app.services.advanced_rag import AdvancedAgenticRAGService, advanced_rag_model_contract
from app.services.rag import HybridRetrievalResult, HybridRetrievalService

ROOT = Path(__file__).resolve().parents[2]


def _hit(chunk: str, domain: RAGDomain, text: str, *, cited: bool = True, source: str | None = None) -> RetrievalHit:
    return RetrievalHit(
        chunk_id=chunk,
        domain=domain,
        score=0.85,
        rerank_score=0.85,
        text=text,
        parent_chunk_id=None,
        citation={"page_number": 2, "source_locator": {"page": 2}} if cited else {},
        metadata={
            "source_id": source or f"src-{chunk}",
            "source_version": "v1",
            "authority_rank": 90,
            "evidence_confidence": 0.9,
        },
        retrieval_sources=("dense", "sparse"),
    )


def _scope(*domains: RAGDomain) -> RetrievalScope:
    return RetrievalScope(
        tenant_id="tenant-1",
        claim_id="claim-1",
        patient_subject_id="patient-1",
        domains=domains,
        acl_tags=("claim_authorized", "user:u1"),
    )


def test_advanced_query_rewriting_and_hyde_for_policy():
    scope = _scope(RAGDomain.POLICY, RAGDomain.CLAIM)
    directive = AgentDirectedRetrievalPlanner().plan(agent=AgentName.POLICY, scope=scope)
    plan = AdvancedQueryPlanner().plan(
        "Please find the authoritative policy coverage exclusion for this service",
        scope=scope,
        directive=directive,
    )
    assert plan.route.mode == RoutingMode.HYBRID_HYDE
    assert plan.hypothetical_document and "Hypothetical retrieval passage only" in plan.hypothetical_document
    assert set(plan.query_plan.domains).issubset(set(scope.domains))
    assert plan.query_plan.minimum_authority_rank >= 70
    assert any(p.field == "minimum_authority_rank" for p in plan.metadata_predicates)


def test_exact_code_route_keeps_lexical_signal():
    scope = _scope(RAGDomain.CODING, RAGDomain.INVOICE)
    directive = AgentDirectedRetrievalPlanner().plan(agent=AgentName.CODING, scope=scope)
    plan = AdvancedQueryPlanner().plan("Check CPT 99213 against billed evidence", scope=scope, directive=directive)
    assert plan.route.mode == RoutingMode.EXACT
    assert plan.route.strategy == RetrievalStrategy.HYBRID
    assert "99213" in plan.query_plan.exact_terms
    assert plan.hypothetical_document is None


def test_self_query_metadata_is_allowlisted_and_narrowing():
    scope = replace(_scope(RAGDomain.HOSPITAL), minimum_authority_rank=60)
    directive = AgentDirectedRetrievalPlanner().plan(agent=AgentName.HOSPITAL_VERIFICATION, scope=scope)
    plan = AdvancedQueryPlanner().plan(
        "Find authoritative FHIR hospital record after 2026-01-01 before 2026-03-01",
        scope=scope,
        directive=directive,
    )
    assert {p.field for p in plan.metadata_predicates} <= {"service_date_from", "service_date_to", "minimum_authority_rank", "source_type"}
    assert str(plan.query_plan.service_date_from) == "2026-01-01"
    assert str(plan.query_plan.service_date_to) == "2026-03-01"
    assert plan.query_plan.minimum_authority_rank >= 70


def test_agent_directive_cannot_broaden_authorized_domain():
    scope = _scope(RAGDomain.POLICY)
    directive = AgentDirectedRetrievalPlanner().plan(agent=AgentName.DECISION_SUPPORT, scope=scope)
    assert directive.domains == (RAGDomain.POLICY,)
    plan = AdvancedQueryPlanner().plan("Compare policy and coding evidence", scope=scope, directive=directive)
    assert set(plan.query_plan.domains) == {RAGDomain.POLICY}


def test_prepared_hybrid_plan_rejects_domain_broadening():
    plan = QueryPlan(
        original_query="x", normalized_query="x", variants=("x",), subqueries=("x",),
        domains=(RAGDomain.POLICY, RAGDomain.CODING), planner_version="test",
    )
    with pytest.raises(PermissionError, match="broaden authorized domains"):
        HybridRetrievalService._validate_prepared_plan(plan, _scope(RAGDomain.POLICY))


def test_citation_enforcer_drops_uncited_material_in_strict_mode():
    hits = [_hit("good", RAGDomain.POLICY, "covered service"), _hit("bad", RAGDomain.POLICY, "uncited", cited=False)]
    accepted, checks, coverage = CitationEnforcer().verify(hits, strict=True)
    assert [x.chunk_id for x in accepted] == ["good"]
    assert coverage == 0.5
    assert next(c for c in checks if c.chunk_id == "bad").valid is False


def test_knowledge_gap_detector_blocks_missing_exact_code():
    scope = _scope(RAGDomain.CODING)
    directive = AgentDirectedRetrievalPlanner().plan(agent=AgentName.CODING, scope=scope)
    plan = AdvancedQueryPlanner().plan("Check CPT 99213", scope=scope, directive=directive)
    hit = _hit("h1", RAGDomain.CODING, "Evidence describes CPT 99214")
    assessment = RetrievalAssessment(confidence=0.8, coverage=0.8, source_diversity=1.0, no_evidence=False)
    gaps, answerability = KnowledgeGapDetector().detect(plan=plan, hits=[hit], assessment=assessment, citation_coverage=1.0)
    assert answerability == Answerability.INSUFFICIENT
    assert "exact_term_not_grounded" in {g.code for g in gaps}


class _FakeRetriever:
    def __init__(self):
        self.calls = []

    def search(self, **kwargs):
        self.calls.append(kwargs)
        idx = len(self.calls)
        if idx == 1:
            hits = (_hit("p1", RAGDomain.POLICY, "Policy coverage applies with source version and citation."),)
        else:
            hits = (
                _hit("p1", RAGDomain.POLICY, "Policy coverage applies with source version and citation."),
                _hit("c1", RAGDomain.CLAIM, "Claim evidence confirms service and coverage context."),
            )
        plan = kwargs["prepared_plan"]
        return HybridRetrievalResult(
            retrieval_run_id=f"retr-{idx}", query=kwargs["query"], plan=plan, hits=hits,
            assessment=RetrievalAssessment(0.8, 0.8, 1.0, False), fallback_steps=(), latency_ms=5,
        )


def test_advanced_service_runs_bounded_second_pass_for_gap():
    fake = _FakeRetriever()
    svc = AdvancedAgenticRAGService(retriever=fake, max_rounds=2)
    result = svc.search(
        query="Compare policy and claim coverage evidence",
        scope=_scope(RAGDomain.POLICY, RAGDomain.CLAIM),
        agent=AgentName.DECISION_SUPPORT,
        limit=4,
    )
    assert result.rounds_executed == 2
    assert len(fake.calls) == 2
    assert result.answerability in {Answerability.ANSWERABLE, Answerability.PARTIAL}
    for call in fake.calls:
        assert call["scope"].tenant_id == "tenant-1"
        assert call["scope"].claim_id == "claim-1"
        assert call["scope"].acl_tags == ("claim_authorized", "user:u1")


def test_advanced_service_source_type_self_query_only_narrows():
    fake = _FakeRetriever()
    svc = AdvancedAgenticRAGService(retriever=fake, max_rounds=1)
    svc.search(
        query="Find FHIR hospital record",
        scope=replace(_scope(RAGDomain.HOSPITAL), source_types=("fhir_resource", "hospital")),
        agent=AgentName.HOSPITAL_VERIFICATION,
        limit=2,
    )
    assert set(fake.calls[0]["scope"].source_types) <= {"fhir_resource", "hospital"}


def test_advanced_model_contract_keeps_authorization_deterministic():
    contract = advanced_rag_model_contract()
    assert contract["architecture"] == "bounded-agentic-rag"
    safety = " ".join(contract["security_invariants"]).lower()
    assert "never broaden" in safety
    assert "knowledge lifecycle" in safety


def test_advanced_rag_migration_has_forced_rls_and_immutable_history():
    migration = (ROOT / "backend/alembic/versions/0026_advanced_agentic_rag.py").read_text()
    assert 'FORCE ROW LEVEL SECURITY' in migration
    assert 'advanced_rag_runs' in migration and 'advanced_rag_events' in migration
    assert 'medclaimiq_reject_immutable_change' in migration


def test_release_policy_requires_advanced_rag_gate():
    policy = json.loads((ROOT / "config/release_engineering_policy.json").read_text())
    assert "advanced-rag-quality" in policy["gates"]["required"]
    workflow = (ROOT / ".github/workflows/release-promotion.yml").read_text()
    assert "--gate advanced-rag-quality=pass" in workflow


def test_advanced_rag_api_registered_and_public_model_only():
    main = (ROOT / "backend/app/main.py").read_text()
    assert "advanced_rag_router" in main
    assert 'f"{settings.api_v1_prefix}/advanced-rag-model"' in main
    api = (ROOT / "backend/app/api/v1/advanced_rag.py").read_text()
    assert '/claims/{claim_id}/rag/advanced-search' in api
    assert '/claims/{claim_id}/rag/advanced-plan' in api
    assert 'Permission.CLAIM_VIEW_AI_FINDINGS' in api


def test_advanced_eval_dataset_and_workflow_exist():
    dataset = json.loads((ROOT / "sample-data/advanced_rag_eval_v1.json").read_text())
    assert dataset["dataset_version"] == "advanced-rag-v1"
    assert len(dataset["cases"]) >= 5
    workflow = (ROOT / ".github/workflows/advanced-rag-quality-gate.yml").read_text()
    assert "run_advanced_rag_evaluations.py --gate" in workflow
