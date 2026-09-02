from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from app.domain.cross_source_rag import FHIRQueryPlan, GraphQueryPlan, RetrieverKind, StructuredFact, StructuredQueryPlan


@dataclass(frozen=True, slots=True)
class CrossSourcePlan:
    retrievers: tuple[RetrieverKind, ...]
    structured: StructuredQueryPlan
    fhir: FHIRQueryPlan
    graph: GraphQueryPlan
    planner_version: str = "cross-source-planner-v1"


class DeterministicCrossSourcePlanner:
    """Maps a reviewer question to typed retrieval operations; never emits SQL text."""

    def plan(
        self,
        *,
        query: str,
        claim_id: str,
        requested_retrievers: tuple[RetrieverKind, ...] = (),
        service_date_from: date | None = None,
        service_date_to: date | None = None,
        graph_max_depth: int = 2,
    ) -> CrossSourcePlan:
        normalized = " ".join(query.lower().split())
        facts: list[StructuredFact] = [StructuredFact.CLAIM]
        resource_types: list[str] = []
        relationships: list[str] = []

        def any_word(*words: str) -> bool:
            return any(re.search(rf"\b{re.escape(word)}\b", normalized) for word in words)

        if any_word("line", "code", "cpt", "hcpcs", "amount", "invoice", "bill"):
            facts.append(StructuredFact.CLAIM_LINES)
        if any_word("policy", "coverage", "eligible", "eligibility", "benefit", "authorization"):
            facts.append(StructuredFact.POLICY)
            resource_types.extend(["Coverage", "ExplanationOfBenefit"])
            relationships.extend(["covered_by", "paid_by"])
        if any_word("encounter", "hospital", "visit", "admission", "discharge", "service"):
            facts.append(StructuredFact.ENCOUNTER)
            resource_types.extend(["Encounter", "DocumentReference"])
            relationships.extend(["occurred_during", "supports"])
        if any_word("provider", "practitioner", "doctor", "facility"):
            facts.append(StructuredFact.PROVIDER)
            resource_types.extend(["Organization", "Practitioner"])
            relationships.extend(["provided_by", "billed_by"])
        if any_word("conflict", "contradiction", "mismatch", "different", "discrepancy"):
            facts.append(StructuredFact.CONTRADICTIONS)
            relationships.append("contradicts")

        if not resource_types:
            resource_types = ["Claim", "ExplanationOfBenefit", "Encounter", "Coverage", "DocumentReference"]
        if not relationships:
            relationships = ["supports", "has_line", "covered_by", "occurred_during", "provided_by", "derived_from"]

        retrievers = requested_retrievers or (
            RetrieverKind.SQL, RetrieverKind.FHIR, RetrieverKind.GRAPH, RetrieverKind.VECTOR,
        )
        return CrossSourcePlan(
            retrievers=tuple(dict.fromkeys(retrievers)),
            structured=StructuredQueryPlan(
                facts=tuple(dict.fromkeys(facts)), claim_id=claim_id,
                service_date_from=service_date_from, service_date_to=service_date_to,
            ),
            fhir=FHIRQueryPlan(claim_id=claim_id, resource_types=tuple(dict.fromkeys(resource_types))),
            graph=GraphQueryPlan(
                claim_id=claim_id, relationship_types=tuple(dict.fromkeys(relationships)),
                max_depth=graph_max_depth,
                as_of=service_date_from if service_date_from == service_date_to else None,
            ),
        )
