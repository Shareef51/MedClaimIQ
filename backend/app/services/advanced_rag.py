from __future__ import annotations

import hashlib
import uuid
from dataclasses import replace
from datetime import UTC, datetime
from time import perf_counter

from app.domain.advanced_rag import AdvancedRAGResult, Answerability, MetadataPredicate
from app.domain.orchestration import AgentName
from app.domain.rag import RAGDomain, RetrievalScope
from app.models.advanced_rag import AdvancedRAGEventModel, AdvancedRAGRunModel
from app.rag.advanced_query import AdvancedQueryPlanner
from app.rag.advanced_reranking import AdvancedEvidenceReranker
from app.rag.agent_retrieval import AgentDirectedRetrievalPlanner
from app.rag.assessment import assess_retrieval
from app.rag.citation_compression import CitationWindowCompressor
from app.rag.citation_enforcement import CitationEnforcer
from app.rag.fusion import reciprocal_rank_fusion
from app.rag.knowledge_gap import KnowledgeGapDetector
from app.rag.reranking import diversify_candidates
from app.repositories.advanced_rag import AdvancedRAGRepository
from app.services.rag import HybridRetrievalService


class AdvancedAgenticRAGService:
    """Bounded advanced retrieval orchestration.

    Authorization is not delegated to query planners or agents. The incoming RetrievalScope is
    authoritative; every derived scope is equal or narrower and the underlying vector store still
    applies tenant/claim/ACL filters before candidates are returned.
    """

    def __init__(
        self,
        *,
        retriever: HybridRetrievalService,
        repository: AdvancedRAGRepository | None = None,
        planner: AdvancedQueryPlanner | None = None,
        agent_planner: AgentDirectedRetrievalPlanner | None = None,
        reranker: AdvancedEvidenceReranker | None = None,
        compressor: CitationWindowCompressor | None = None,
        citation_enforcer: CitationEnforcer | None = None,
        gap_detector: KnowledgeGapDetector | None = None,
        max_rounds: int = 2,
    ) -> None:
        self.retriever = retriever
        self.repository = repository
        self.planner = planner or AdvancedQueryPlanner()
        self.agent_planner = agent_planner or AgentDirectedRetrievalPlanner()
        self.reranker = reranker or AdvancedEvidenceReranker()
        self.compressor = compressor or CitationWindowCompressor()
        self.citation_enforcer = citation_enforcer or CitationEnforcer()
        self.gap_detector = gap_detector or KnowledgeGapDetector()
        self.max_rounds = max(1, min(2, max_rounds))

    def plan_only(self, *, query: str, scope: RetrievalScope, agent: AgentName | None, enable_hyde: bool = True):
        directive = self.agent_planner.plan(agent=agent, scope=scope)
        return self.planner.plan(query, scope=scope, directive=directive, enable_hyde=enable_hyde)

    def search(
        self,
        *,
        query: str,
        scope: RetrievalScope,
        agent: AgentName | None = None,
        limit: int = 8,
        enable_hyde: bool = True,
        strict_citations: bool = True,
        trace_id: str | None = None,
    ) -> AdvancedRAGResult:
        if not query.strip():
            raise ValueError("query cannot be empty")
        if limit <= 0:
            raise ValueError("limit must be positive")
        if self.repository is not None and scope.tenant_id != self.repository.tenant_id:
            raise PermissionError("cross-tenant advanced RAG retrieval denied")

        started = perf_counter()
        directive = self.agent_planner.plan(agent=agent, scope=scope)
        advanced_plan = self.planner.plan(query, scope=scope, directive=directive, enable_hyde=enable_hyde)
        effective_scope = self._narrow_scope(scope, advanced_plan.metadata_predicates, advanced_plan.query_plan.domains, advanced_plan.query_plan.minimum_authority_rank, advanced_plan.query_plan.service_date_from, advanced_plan.query_plan.service_date_to)

        rounds_allowed = min(self.max_rounds, directive.max_rounds)
        first = self.retriever.search(
            query=query,
            scope=effective_scope,
            limit=max(limit, 8),
            hydrate_parent=True,
            compress_context=False,
            strategy=advanced_plan.route.strategy,
            trace_id=trace_id,
            prepared_plan=advanced_plan.query_plan,
            candidate_multiplier_override=advanced_plan.route.candidate_multiplier,
        )
        ranked_lists = [list(first.hits)]
        retrieval_run_id = first.retrieval_run_id
        fallback_steps = list(first.fallback_steps)
        rounds = 1

        selected, assessment, checks, citation_coverage, gaps, answerability = self._finalize(
            query=query,
            plan=advanced_plan,
            ranked_lists=ranked_lists,
            limit=limit,
            strict_citations=strict_citations,
        )

        if answerability != Answerability.ANSWERABLE and rounds_allowed > 1:
            refinement = self._gap_refinement(query, advanced_plan, gaps)
            refined_query_plan = replace(
                advanced_plan.query_plan,
                variants=tuple(dict.fromkeys((*advanced_plan.query_plan.variants, refinement)))[:8],
                subqueries=tuple(dict.fromkeys((*advanced_plan.query_plan.subqueries, refinement)))[:6],
            )
            second = self.retriever.search(
                query=refinement,
                scope=effective_scope,
                limit=max(limit, 8),
                hydrate_parent=True,
                compress_context=False,
                strategy=advanced_plan.route.strategy,
                trace_id=trace_id,
                prepared_plan=refined_query_plan,
                candidate_multiplier_override=min(8, advanced_plan.route.candidate_multiplier + 1),
            )
            ranked_lists.append(list(second.hits))
            retrieval_run_id = second.retrieval_run_id
            fallback_steps.extend(("knowledge_gap_second_pass", *second.fallback_steps))
            rounds = 2
            selected, assessment, checks, citation_coverage, gaps, answerability = self._finalize(
                query=query,
                plan=advanced_plan,
                ranked_lists=ranked_lists,
                limit=limit,
                strict_citations=strict_citations,
            )

        latency_ms = max(0, int((perf_counter() - started) * 1000))
        run_id = f"arag_{uuid.uuid4().hex}"
        result = AdvancedRAGResult(
            advanced_run_id=run_id,
            retrieval_run_id=retrieval_run_id,
            query=query,
            plan=advanced_plan,
            hits=tuple(selected),
            assessment=assessment,
            citations=checks,
            citation_coverage=citation_coverage,
            knowledge_gaps=gaps,
            answerability=answerability,
            rounds_executed=rounds,
            fallback_steps=tuple(dict.fromkeys(fallback_steps)),
            latency_ms=latency_ms,
            trace_id=trace_id,
            diagnostics={
                "scope_preserved": True,
                "tenant_filter": "mandatory",
                "claim_filter": "mandatory when claim-scoped",
                "acl_filter": "mandatory",
                "knowledge_governance_filter": "postgresql lifecycle + qdrant projection",
                "transformation_hashes": list(advanced_plan.transformation_hashes),
            },
        )
        if self.repository is not None:
            self._persist(result, scope=scope, agent=agent)
        return result

    def _finalize(self, *, query, plan, ranked_lists, limit, strict_citations):
        fused = reciprocal_rank_fusion(ranked_lists, k=60) if len(ranked_lists) > 1 else list(ranked_lists[0])
        reranked = self.reranker.rerank(query=query, hits=fused, plan=plan)
        diversified = diversify_candidates(reranked, limit=limit)
        compressed = self.compressor.compress(query, diversified)
        cited, checks, citation_coverage = self.citation_enforcer.verify(compressed, strict=strict_citations)
        assessment = assess_retrieval(cited, plan=plan.query_plan, minimum_confidence=self.gap_detector.minimum_confidence)
        gaps, answerability = self.gap_detector.detect(plan=plan, hits=cited, assessment=assessment, citation_coverage=citation_coverage)
        return cited, assessment, checks, citation_coverage, gaps, answerability

    @staticmethod
    def _narrow_scope(scope: RetrievalScope, predicates: tuple[MetadataPredicate, ...], domains, authority, service_from, service_to) -> RetrievalScope:
        authorized_domains = set(scope.domains or tuple(RAGDomain))
        narrowed_domains = tuple(d for d in domains if d in authorized_domains)
        if not narrowed_domains:
            narrowed_domains = tuple(scope.domains or tuple(RAGDomain))
        source_types = tuple(scope.source_types)
        for predicate in predicates:
            if predicate.field == "source_type":
                proposed = tuple(str(x) for x in predicate.value)
                source_types = tuple(x for x in proposed if x in set(source_types)) if source_types else proposed
        return replace(
            scope,
            domains=narrowed_domains,
            source_types=source_types,
            service_date_from=service_from,
            service_date_to=service_to,
            minimum_authority_rank=max(scope.minimum_authority_rank, int(authority)),
        )

    @staticmethod
    def _gap_refinement(query, plan, gaps) -> str:
        missing_domains = sorted({g.domain.value for g in gaps if g.domain is not None})
        evidence = ", ".join(plan.agent_directive.required_evidence_types[:4])
        suffix = " ".join(missing_domains) if missing_domains else "additional authoritative evidence"
        return f"{query} {suffix} required evidence: {evidence}"[:900]

    def _persist(self, result: AdvancedRAGResult, *, scope: RetrievalScope, agent: AgentName | None) -> None:
        assert self.repository is not None
        now = datetime.now(UTC)
        predicates = [
            {"field": p.field, "operator": p.operator.value, "value_sha256": hashlib.sha256(str(p.value).encode()).hexdigest()}
            for p in result.plan.metadata_predicates
        ]
        run = AdvancedRAGRunModel(
            advanced_run_id=result.advanced_run_id,
            tenant_id=scope.tenant_id,
            claim_id=scope.claim_id or "",
            retrieval_run_id=result.retrieval_run_id,
            query_sha256=hashlib.sha256(result.query.encode()).hexdigest(),
            query_length=len(result.query),
            agent_name=agent.value if agent else None,
            query_intent=result.plan.intent.value,
            routing_mode=result.plan.route.mode.value,
            retrieval_strategy=result.plan.route.strategy.value,
            planner_version=result.plan.planner_version,
            reranker_version=self.reranker.version,
            rewrite_count=len(result.plan.rewrites),
            hyde_used=bool(result.plan.hypothetical_document),
            model_assisted=result.plan.model_assisted,
            requested_domains=[d.value for d in scope.domains],
            planned_domains=[d.value for d in result.plan.query_plan.domains],
            metadata_predicates=predicates,
            confidence=result.assessment.confidence,
            coverage=result.assessment.coverage,
            citation_coverage=result.citation_coverage,
            answerability=result.answerability.value,
            knowledge_gap_count=len(result.knowledge_gaps),
            rounds_executed=result.rounds_executed,
            selected_count=len(result.hits),
            latency_ms=result.latency_ms,
            trace_id=result.trace_id,
        )
        events = [
            AdvancedRAGEventModel(
                event_id=f"arge_{uuid.uuid4().hex}", tenant_id=scope.tenant_id, claim_id=scope.claim_id or "",
                advanced_run_id=result.advanced_run_id, event_type="advanced_rag.plan.created",
                payload_summary={
                    "intent": result.plan.intent.value,
                    "route": result.plan.route.mode.value,
                    "rewrite_hashes": list(result.plan.transformation_hashes),
                    "planned_domains": [d.value for d in result.plan.query_plan.domains],
                }, created_at=now,
            ),
            AdvancedRAGEventModel(
                event_id=f"arge_{uuid.uuid4().hex}", tenant_id=scope.tenant_id, claim_id=scope.claim_id or "",
                advanced_run_id=result.advanced_run_id, event_type="advanced_rag.assessed",
                payload_summary={
                    "answerability": result.answerability.value,
                    "confidence": result.assessment.confidence,
                    "citation_coverage": result.citation_coverage,
                    "gap_codes": [g.code for g in result.knowledge_gaps],
                    "selected_count": len(result.hits),
                }, created_at=now,
            ),
        ]
        self.repository.add_run(run, events)


def advanced_rag_model_contract() -> dict[str, object]:
    return {
        "architecture": "bounded-agentic-rag",
        "query_intelligence": [
            "deterministic rewriting",
            "optional schema-constrained model rewriting",
            "HyDE-style hypothetical retrieval documents",
            "self-query metadata extraction from allowlisted fields",
        ],
        "routing": ["adaptive dense/sparse/hybrid selection", "agent-directed domain planning", "bounded second-pass retrieval"],
        "ranking": ["hybrid RRF", "evidence-aware reranking", "advanced authority/citation reranking", "source diversification"],
        "context": ["parent hydration", "citation-window compression", "exact source/version preservation"],
        "verification": ["citation enforcement", "confidence assessment", "knowledge-gap detection", "explicit insufficient-evidence state"],
        "security_invariants": [
            "tenant/claim/ACL scope originates from persisted authorization",
            "planner output may narrow but never broaden authorized scope",
            "Qdrant filters are applied before candidate return",
            "Release 30 PostgreSQL knowledge lifecycle remains authoritative",
            "retired/future/expired governed knowledge is excluded",
            "model-assisted transformations never control authorization metadata",
        ],
        "persistence": "query hashes/transformation hashes and plan summaries only; no raw query or hypothetical document in advanced telemetry",
        "human_boundary": "knowledge gaps and insufficient evidence route toward more evidence/human review, never autonomous claim approval or denial",
    }
