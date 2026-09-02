from __future__ import annotations

import json

from app.domain.cross_source_rag import EvidenceItem, FHIRQueryPlan, RetrieverKind, UnifiedCitation, evidence_key
from app.domain.evidence_graph import authority_rank
from app.repositories.cross_source_rag import CrossSourceRepository


class FHIRStructuredRetriever:
    def __init__(self, repository: CrossSourceRepository) -> None:
        self.repository = repository

    def retrieve(self, plan: FHIRQueryPlan) -> tuple[EvidenceItem, ...]:
        items: list[EvidenceItem] = []
        for row in self.repository.fhir_snapshots(plan):
            canonical = dict(row.canonical_resource or {})
            text = json.dumps(canonical, sort_keys=True, default=str, separators=(",", ":"))
            if len(text) > 3500:
                text = text[:3500] + "…"
            source_kind = {
                "Encounter": "fhir_encounter", "ExplanationOfBenefit": "fhir_eob",
                "Coverage": "fhir_coverage", "Claim": "fhir_claim",
            }.get(row.resource_type, "fhir_claim")
            citation = UnifiedCitation(
                source_type="fhir", source_id=f"{row.resource_type}/{row.logical_id}", source_version=row.version_id,
                locator={"source_url": row.source_url, "snapshot_id": row.snapshot_id},
            )
            items.append(EvidenceItem(
                evidence_key=evidence_key("fhir", row.connection_id, row.resource_type, row.logical_id, row.version_id),
                retriever=RetrieverKind.FHIR, source_type="fhir", source_id=f"{row.resource_type}/{row.logical_id}",
                source_version=row.version_id, text=text, authority_rank=authority_rank(source_kind),
                confidence=0.99 if row.authoritative else 0.85, citation=citation,
                metadata={"snapshot_id": row.snapshot_id, "content_sha256": row.content_sha256, "authoritative": row.authoritative},
            ))
        return tuple(items)
