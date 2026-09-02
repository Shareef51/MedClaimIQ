from types import SimpleNamespace
from datetime import date, datetime, timezone
from decimal import Decimal

from app.domain.cross_source_rag import (
    ContradictionSummary, EvidenceItem, FHIRQueryPlan, GraphQueryPlan, RetrieverKind,
    StructuredFact, StructuredQueryPlan, UnifiedCitation, evidence_key,
)
from app.rag.evidence_fusion import CrossSourceEvidenceFusion
from app.rag.fhir_retrieval import FHIRStructuredRetriever
from app.rag.graph_retrieval import BoundedGraphRAGRetriever
from app.rag.structured_retrieval import StructuredSQLRetriever


class FakeRepo:
    def structured_rows(self, plan):
        return {
            StructuredFact.CLAIM: [SimpleNamespace(
                claim_id="claim-1", status="verifying", total_amount=Decimal("150.00"), currency="USD",
                service_from=date(2026, 8, 10), service_to=None, policy_id="policy-1", encounter_id="enc-1",
            )],
            StructuredFact.CLAIM_LINES: [SimpleNamespace(
                claim_line_id="line-1", line_number=1, code_system="CPT", service_code="99213",
                service_date=date(2026, 8, 10), units=Decimal("1"), amount=Decimal("150.00"),
            )],
        }
    def fhir_snapshots(self, plan):
        return [SimpleNamespace(
            connection_id="hospital-1", resource_type="ExplanationOfBenefit", logical_id="eob-1", version_id="2",
            canonical_resource={"resource_type":"ExplanationOfBenefit","total":"125.00"}, source_url="https://hospital.invalid/fhir/ExplanationOfBenefit/eob-1",
            snapshot_id="snap-1", authoritative=True, content_sha256="a"*64,
        )]
    def claim_entities(self, claim_id, limit=50):
        return [
            SimpleNamespace(entity_id="ce-claim", entity_type="claim", canonical_key="claim-1"),
            SimpleNamespace(entity_id="ce-line", entity_type="claim_line", canonical_key="line-1"),
            SimpleNamespace(entity_id="ce-eob", entity_type="eob", canonical_key="eob-1"),
        ]
    def graph_edges_for_claim(self, claim_id, relationship_types=(), as_of=None, max_edges=100):
        return [
            SimpleNamespace(edge_id="edge-1", source_entity_id="ce-claim", target_entity_id="ce-line", relationship_type="has_line", authority_rank=78, confidence=Decimal("0.98")),
            SimpleNamespace(edge_id="edge-2", source_entity_id="ce-eob", target_entity_id="ce-claim", relationship_type="supports", authority_rank=92, confidence=Decimal("0.95")),
        ][:max_edges]


def test_structured_sql_retriever_returns_whitelisted_claim_facts():
    plan = StructuredQueryPlan(facts=(StructuredFact.CLAIM, StructuredFact.CLAIM_LINES), claim_id="claim-1")
    items = StructuredSQLRetriever(FakeRepo()).retrieve(plan)
    assert len(items) == 2
    assert all(item.retriever is RetrieverKind.SQL for item in items)
    assert any("CPT 99213" in item.text for item in items)


def test_fhir_retriever_preserves_versioned_citation():
    items = FHIRStructuredRetriever(FakeRepo()).retrieve(FHIRQueryPlan(claim_id="claim-1", resource_types=("ExplanationOfBenefit",)))
    assert items[0].citation.source_version == "2"
    assert items[0].citation.locator["snapshot_id"] == "snap-1"
    assert items[0].authority_rank == 92


def test_graph_retriever_returns_bounded_paths_with_edge_citations():
    items = BoundedGraphRAGRetriever(FakeRepo()).retrieve(GraphQueryPlan(claim_id="claim-1", max_depth=2, max_edges=1))
    assert len(items) == 1
    assert items[0].retriever is RetrieverKind.GRAPH
    assert items[0].citation.locator["edge_id"] == "edge-1"
    assert items[0].citation.relationship_path == ("has_line",)


def _item(retriever, source_id, authority, confidence):
    return EvidenceItem(
        evidence_key=evidence_key(retriever.value, source_id), retriever=retriever,
        source_type=retriever.value, source_id=source_id, text=f"evidence from {source_id}",
        authority_rank=authority, confidence=confidence,
        citation=UnifiedCitation(source_type=retriever.value, source_id=source_id),
    )


def test_fusion_scores_cross_source_coverage_and_preserves_contradictions():
    contradiction = ContradictionSummary("con-1", "amount", "material", 0.95, {"value":"150"}, {"value":"125"}, "open")
    pack = CrossSourceEvidenceFusion().fuse(
        claim_id="claim-1", query="compare amount",
        items=(
            _item(RetrieverKind.SQL, "claim-1", 78, .98),
            _item(RetrieverKind.FHIR, "eob-1", 92, .99),
            _item(RetrieverKind.GRAPH, "edge-1", 92, .95),
            _item(RetrieverKind.VECTOR, "chunk-1", 80, .9),
        ), contradictions=(contradiction,),
        planned_retrievers=(RetrieverKind.SQL, RetrieverKind.FHIR, RetrieverKind.GRAPH, RetrieverKind.VECTOR),
        executed_retrievers=(RetrieverKind.SQL, RetrieverKind.FHIR, RetrieverKind.GRAPH, RetrieverKind.VECTOR),
        planner_version="v1",
    )
    assert pack.assessment.coverage == 1.0
    assert pack.assessment.unresolved_material_contradictions == 1
    assert "unresolved_material_contradictions" in pack.assessment.reasons
    assert pack.contradictions[0].left_value == {"value":"150"}


def test_fusion_returns_explicit_no_evidence():
    pack = CrossSourceEvidenceFusion().fuse(
        claim_id="claim-1", query="unknown", items=(), contradictions=(),
        planned_retrievers=(RetrieverKind.SQL, RetrieverKind.FHIR), executed_retrievers=(RetrieverKind.SQL, RetrieverKind.FHIR),
        planner_version="v1",
    )
    assert pack.assessment.no_evidence is True
    assert "no_cross_source_evidence" in pack.assessment.reasons
