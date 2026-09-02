from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Iterable

from app.domain.rag import CitationAnchor, KnowledgeDocument, RAGDomain, SourceSegment, sanitize_acl_tags


def infer_rag_domain(*, source_type: str, resource_type: str | None = None, attributes: dict[str, object] | None = None) -> RAGDomain:
    haystack = " ".join([source_type or "", resource_type or "", str((attributes or {}).get("document_type", ""))]).lower()
    if any(term in haystack for term in ("fhir", "hospital", "encounter", "eob", "explanationofbenefit")):
        return RAGDomain.HOSPITAL
    if any(term in haystack for term in ("policy", "coverage", "benefit")):
        return RAGDomain.POLICY
    if any(term in haystack for term in ("invoice", "bill", "receipt")):
        return RAGDomain.INVOICE
    if any(term in haystack for term in ("cpt", "hcpcs", "icd", "snomed", "loinc", "coding")):
        return RAGDomain.CODING
    if any(term in haystack for term in ("history", "historical", "prior_claim")):
        return RAGDomain.HISTORICAL_CLAIMS
    if "claim" in haystack:
        return RAGDomain.CLAIM
    return RAGDomain.EVIDENCE


def document_from_extraction_units(
    *,
    tenant_id: str,
    claim_id: str,
    patient_subject_id: str,
    source_evidence_id: str,
    source_version: str,
    source_content_sha256: str | None,
    units: Iterable[object],
    source_type: str = "evidence",
    domain: RAGDomain | None = None,
    authority_rank: int = 60,
    evidence_confidence: Decimal | float = 0.75,
    entity_ids: Iterable[str] = (),
    relationship_types: Iterable[str] = (),
    acl_tags: Iterable[str] = ("claim_authorized",),
    service_date: date | None = None,
    attributes: dict[str, object] | None = None,
) -> KnowledgeDocument:
    segments: list[SourceSegment] = []
    for unit in units:
        text = getattr(unit, "text_content", None)
        structured = dict(getattr(unit, "structured_data", {}) or {})
        if not text and structured:
            text = "\n".join(f"{key}: {value}" for key, value in sorted(structured.items()))
        if not text:
            continue
        bbox = getattr(unit, "bbox", None)
        citation = CitationAnchor(
            evidence_id=source_evidence_id,
            extraction_unit_id=getattr(unit, "unit_id", None),
            page_number=getattr(unit, "page_number", None),
            start_ms=getattr(unit, "start_ms", None),
            end_ms=getattr(unit, "end_ms", None),
            bbox=tuple(float(item) for item in bbox) if bbox else None,
            frame_index=(dict(getattr(unit, "source_locator", {}) or {}).get("frame_index")),
            frame_sha256=(dict(getattr(unit, "source_locator", {}) or {}).get("frame_sha256")),
            source_locator=dict(getattr(unit, "source_locator", {}) or {}),
        )
        segments.append(
            SourceSegment(
                segment_id=str(getattr(unit, "unit_id", f"unit-{len(segments)}")),
                text=str(text),
                unit_type=str(getattr(unit, "unit_type", "text")),
                citation=citation,
                structured_data=structured,
            )
        )
    attrs = dict(attributes or {})
    resolved_domain = domain or infer_rag_domain(source_type=source_type, attributes=attrs)
    return KnowledgeDocument(
        tenant_id=tenant_id,
        claim_id=claim_id,
        patient_subject_id=patient_subject_id,
        domain=resolved_domain,
        source_type=source_type,
        source_id=source_evidence_id,
        source_version=source_version,
        source_content_sha256=source_content_sha256,
        segments=tuple(segments),
        authority_rank=max(0, min(100, authority_rank)),
        evidence_confidence=float(max(Decimal("0"), min(Decimal("1"), Decimal(str(evidence_confidence))))),
        entity_ids=tuple(sorted(set(entity_ids))),
        relationship_types=tuple(sorted(set(relationship_types))),
        acl_tags=sanitize_acl_tags(acl_tags),
        service_date=service_date,
        attributes=attrs,
    )
