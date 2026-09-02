from __future__ import annotations

from dataclasses import asdict
from datetime import date, datetime, timezone
from decimal import Decimal
from hashlib import sha256
from typing import Any

from app.domain.evidence_graph import (
    CanonicalEntity,
    CanonicalEntityType,
    RelationshipEdge,
    RelationshipType,
    SourceRef,
    authority_rank,
    canonical_entity_id,
    contradiction_for_values,
    evidence_confidence,
    normalize_code,
    relationship_edge_id,
    score_claim_line_crosswalk,
    temporal_alignment,
)


def source_ref_from_fhir(snapshot: Any, *, source_system: str = "fhir") -> SourceRef:
    return SourceRef(
        source_type="fhir",
        source_system=source_system,
        resource_type=str(snapshot.resource_type),
        resource_id=str(snapshot.logical_id),
        version=str(snapshot.version_id),
        content_sha256=str(snapshot.content_sha256),
        locator={"snapshot_id": str(snapshot.snapshot_id), "source_url": str(snapshot.source_url)},
    )


def entity_for_claim(claim: Any) -> CanonicalEntity:
    return CanonicalEntity(
        entity_id=canonical_entity_id(claim.tenant_id, CanonicalEntityType.CLAIM, claim.claim_id),
        tenant_id=claim.tenant_id,
        entity_type=CanonicalEntityType.CLAIM,
        canonical_key=claim.claim_id,
        claim_id=claim.claim_id,
        patient_subject_id=claim.patient_subject_id,
        attributes={"external_claim_ref": claim.external_claim_ref, "claim_type": claim.claim_type},
        valid_from=claim.service_from,
        valid_to=claim.service_to,
    )


def entity_for_claim_line(line: Any, claim: Any) -> CanonicalEntity:
    code = normalize_code(line.code_system, line.service_code)
    return CanonicalEntity(
        entity_id=canonical_entity_id(line.tenant_id, CanonicalEntityType.CLAIM_LINE, line.claim_line_id),
        tenant_id=line.tenant_id,
        entity_type=CanonicalEntityType.CLAIM_LINE,
        canonical_key=line.claim_line_id,
        claim_id=line.claim_id,
        patient_subject_id=claim.patient_subject_id,
        attributes={
            "line_number": line.line_number,
            "canonical_code_system": code.canonical_system if code else line.code_system,
            "canonical_code": code.canonical_code if code else line.service_code,
            "amount": str(line.amount),
            "units": str(line.units),
        },
        valid_from=line.service_date,
        valid_to=line.service_date,
    )


def edges_for_claim(claim: Any, *, claim_entity: CanonicalEntity) -> list[RelationshipEdge]:
    edges: list[RelationshipEdge] = []
    refs = (SourceRef("structured", "medclaimiq", "Claim", claim.claim_id),)

    patient_id = canonical_entity_id(claim.tenant_id, CanonicalEntityType.PATIENT, claim.patient_subject_id)
    provider_id = canonical_entity_id(claim.tenant_id, CanonicalEntityType.ORGANIZATION, claim.provider_organization_id)
    payer_id = canonical_entity_id(claim.tenant_id, CanonicalEntityType.ORGANIZATION, claim.payer_organization_id)

    for source, rel, target in (
        (patient_id, RelationshipType.SUBJECT_OF, claim_entity.entity_id),
        (claim_entity.entity_id, RelationshipType.BILLED_BY, provider_id),
        (claim_entity.entity_id, RelationshipType.PAID_BY, payer_id),
    ):
        edge_id = relationship_edge_id(claim.tenant_id, source, rel, target, (refs[0].stable_key,))
        edges.append(RelationshipEdge(edge_id, claim.tenant_id, source, target, rel, claim.claim_id, Decimal("0.98"), 78, refs, claim.service_from, claim.service_to))

    if claim.policy_id:
        target = canonical_entity_id(claim.tenant_id, CanonicalEntityType.POLICY, claim.policy_id)
        edge_id = relationship_edge_id(claim.tenant_id, claim_entity.entity_id, RelationshipType.COVERED_BY, target, (refs[0].stable_key,))
        edges.append(RelationshipEdge(edge_id, claim.tenant_id, claim_entity.entity_id, target, RelationshipType.COVERED_BY, claim.claim_id, Decimal("0.95"), 78, refs, claim.service_from, claim.service_to))
    if claim.encounter_id:
        target = canonical_entity_id(claim.tenant_id, CanonicalEntityType.ENCOUNTER, claim.encounter_id)
        edge_id = relationship_edge_id(claim.tenant_id, claim_entity.entity_id, RelationshipType.OCCURRED_DURING, target, (refs[0].stable_key,))
        edges.append(RelationshipEdge(edge_id, claim.tenant_id, claim_entity.entity_id, target, RelationshipType.OCCURRED_DURING, claim.claim_id, Decimal("0.95"), 78, refs, claim.service_from, claim.service_to))
    return edges


def edge_fingerprint(edge: RelationshipEdge) -> str:
    return sha256("|".join([edge.tenant_id, edge.source_entity_id, edge.relationship_type.value, edge.target_entity_id, *[r.stable_key for r in edge.provenance]]).encode()).hexdigest()


def contradiction_fingerprint(claim_id: str, field_name: str, left: SourceRef, right: SourceRef, left_value: Any, right_value: Any) -> str:
    material = f"{claim_id}|{field_name}|{left.stable_key}|{right.stable_key}|{left_value!r}|{right_value!r}"
    return sha256(material.encode()).hexdigest()


def graph_model_contract() -> dict[str, Any]:
    return {
        "canonical_entities": [e.value for e in CanonicalEntityType],
        "relationships": [r.value for r in RelationshipType],
        "normalization": [
            "deterministic_canonical_ids",
            "source_to_canonical_version_mapping",
            "code_system_alias_normalization",
            "service_date_temporal_alignment",
            "claim_line_crosswalk_scoring",
        ],
        "evidence_quality": ["source_authority_rank", "integrity_signal", "extraction_confidence", "corroboration"],
        "contradictions": ["field_level", "source_pair_provenance", "materiality", "human_resolution"],
        "graph": ["tenant_scoped_edges", "temporal_edges", "provenance_refs", "bounded_traversal"],
        "rag_metadata": ["tenant_id", "claim_id", "patient_subject_id", "entity_ids", "relationships", "source_version", "authority", "confidence", "ACL", "temporal_alignment"],
        "safety": "Graph construction is deterministic; LLM output cannot create authoritative identity mappings or silent edges.",
    }

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class SourceMappingSpec:
    mapping_id: str
    tenant_id: str
    entity_id: str
    claim_id: str | None
    source_ref: SourceRef
    authority_rank: int
    confidence: Decimal
    observed_at: datetime
    valid_from: date | None = None
    valid_to: date | None = None


@dataclass(frozen=True, slots=True)
class CompiledClaimGraph:
    entities: tuple[CanonicalEntity, ...]
    source_mappings: tuple[SourceMappingSpec, ...]
    edges: tuple[RelationshipEdge, ...]


def _mapping_id(tenant_id: str, entity_id: str, source_ref: SourceRef) -> str:
    return "map_" + sha256(f"{tenant_id}|{entity_id}|{source_ref.stable_key}".encode()).hexdigest()[:32]


def _entity(
    tenant_id: str,
    entity_type: CanonicalEntityType,
    key: str,
    *,
    claim_id: str | None,
    patient_subject_id: str | None,
    attributes: dict[str, Any] | None = None,
    valid_from: date | None = None,
    valid_to: date | None = None,
) -> CanonicalEntity:
    return CanonicalEntity(
        entity_id=canonical_entity_id(tenant_id, entity_type, key),
        tenant_id=tenant_id,
        entity_type=entity_type,
        canonical_key=key,
        claim_id=claim_id,
        patient_subject_id=patient_subject_id,
        attributes=attributes or {},
        valid_from=valid_from,
        valid_to=valid_to,
    )


def _dedupe_entities(values: list[CanonicalEntity]) -> tuple[CanonicalEntity, ...]:
    ordered: dict[str, CanonicalEntity] = {}
    for item in values:
        ordered[item.entity_id] = item
    return tuple(ordered.values())


def compile_claim_graph(
    *,
    claim: Any,
    claim_lines: list[Any] | tuple[Any, ...] = (),
    evidence_artifacts: list[Any] | tuple[Any, ...] = (),
    extraction_units: list[Any] | tuple[Any, ...] = (),
    fhir_snapshots: list[Any] | tuple[Any, ...] = (),
    observed_at: datetime | None = None,
) -> CompiledClaimGraph:
    """Compile existing persisted claim/evidence/FHIR facts into a deterministic graph projection.

    This function performs no LLM reasoning and no database writes, making it independently testable and
    safe to rerun. Persistence can use stable IDs/fingerprints for idempotent insertion.
    """
    now = observed_at or datetime.now(timezone.utc)
    tenant_id = str(claim.tenant_id)
    claim_id = str(claim.claim_id)
    patient_subject_id = str(claim.patient_subject_id)
    entities: list[CanonicalEntity] = []
    mappings: list[SourceMappingSpec] = []
    edges: list[RelationshipEdge] = []

    claim_entity = entity_for_claim(claim)
    patient_entity = _entity(tenant_id, CanonicalEntityType.PATIENT, patient_subject_id, claim_id=claim_id, patient_subject_id=patient_subject_id)
    provider_entity = _entity(tenant_id, CanonicalEntityType.ORGANIZATION, str(claim.provider_organization_id), claim_id=claim_id, patient_subject_id=patient_subject_id)
    payer_entity = _entity(tenant_id, CanonicalEntityType.ORGANIZATION, str(claim.payer_organization_id), claim_id=claim_id, patient_subject_id=patient_subject_id)
    entities.extend([claim_entity, patient_entity, provider_entity, payer_entity])

    if getattr(claim, "policy_id", None):
        entities.append(_entity(tenant_id, CanonicalEntityType.POLICY, str(claim.policy_id), claim_id=claim_id, patient_subject_id=patient_subject_id, valid_from=claim.service_from, valid_to=claim.service_to))
    if getattr(claim, "encounter_id", None):
        entities.append(_entity(tenant_id, CanonicalEntityType.ENCOUNTER, str(claim.encounter_id), claim_id=claim_id, patient_subject_id=patient_subject_id, valid_from=claim.service_from, valid_to=claim.service_to))

    claim_source = SourceRef("structured", "medclaimiq", "Claim", claim_id, str(getattr(claim, "status_version", "1")))
    mappings.append(SourceMappingSpec(_mapping_id(tenant_id, claim_entity.entity_id, claim_source), tenant_id, claim_entity.entity_id, claim_id, claim_source, authority_rank("structured_claim_db"), Decimal("0.99000"), now, claim.service_from, claim.service_to))
    edges.extend(edges_for_claim(claim, claim_entity=claim_entity))

    for line in claim_lines:
        line_entity = entity_for_claim_line(line, claim)
        entities.append(line_entity)
        line_source = SourceRef("structured", "medclaimiq", "ClaimLine", str(line.claim_line_id), "1")
        mappings.append(SourceMappingSpec(_mapping_id(tenant_id, line_entity.entity_id, line_source), tenant_id, line_entity.entity_id, claim_id, line_source, authority_rank("structured_claim_db"), Decimal("0.99000"), now, line.service_date, line.service_date))
        edge_id = relationship_edge_id(tenant_id, claim_entity.entity_id, RelationshipType.HAS_LINE, line_entity.entity_id, [line_source.stable_key])
        edges.append(RelationshipEdge(edge_id, tenant_id, claim_entity.entity_id, line_entity.entity_id, RelationshipType.HAS_LINE, claim_id, Decimal("0.99000"), authority_rank("structured_claim_db"), (line_source,), line.service_date, line.service_date))

    for evidence in evidence_artifacts:
        if str(getattr(evidence, "claim_id", "")) != claim_id:
            continue
        evidence_entity = _entity(tenant_id, CanonicalEntityType.EVIDENCE, str(evidence.evidence_id), claim_id=claim_id, patient_subject_id=patient_subject_id, attributes={"document_type": evidence.document_type, "media_type": evidence.media_type, "status": evidence.status})
        entities.append(evidence_entity)
        source_kind = "accepted_original_evidence" if str(getattr(evidence, "status", "")) == "accepted" else "derived_extraction"
        evidence_source = SourceRef(str(evidence.source_type), str(evidence.source_system), "EvidenceArtifact", str(evidence.evidence_id), str(getattr(evidence, "evidence_version", "1")), str(getattr(evidence, "content_sha256", "")) or None, dict(getattr(evidence, "source_locator", {}) or {}))
        confidence = evidence_confidence(authority=authority_rank(source_kind), integrity_verified=bool(getattr(evidence, "verified_at", None)), corroborating_sources=0)
        mappings.append(SourceMappingSpec(_mapping_id(tenant_id, evidence_entity.entity_id, evidence_source), tenant_id, evidence_entity.entity_id, claim_id, evidence_source, authority_rank(source_kind), confidence, now))
        edge_id = relationship_edge_id(tenant_id, evidence_entity.entity_id, RelationshipType.SUPPORTS, claim_entity.entity_id, [evidence_source.stable_key])
        edges.append(RelationshipEdge(edge_id, tenant_id, evidence_entity.entity_id, claim_entity.entity_id, RelationshipType.SUPPORTS, claim_id, confidence, authority_rank(source_kind), (evidence_source,)))

    evidence_entity_ids = {str(e.evidence_id): canonical_entity_id(tenant_id, CanonicalEntityType.EVIDENCE, str(e.evidence_id)) for e in evidence_artifacts if str(getattr(e, "claim_id", "")) == claim_id}
    for unit in extraction_units:
        if str(getattr(unit, "claim_id", "")) != claim_id:
            continue
        unit_entity = _entity(tenant_id, CanonicalEntityType.EXTRACTION_UNIT, str(unit.unit_id), claim_id=claim_id, patient_subject_id=patient_subject_id, attributes={"unit_type": unit.unit_type, "page_number": unit.page_number, "start_ms": unit.start_ms, "end_ms": unit.end_ms})
        entities.append(unit_entity)
        source = SourceRef("derived", "document_intelligence", "ExtractionUnit", str(unit.unit_id), "1", str(unit.content_sha256), dict(unit.citation_anchor or unit.source_locator or {}))
        confidence = evidence_confidence(authority=authority_rank("derived_extraction"), integrity_verified=True, extraction_confidence=Decimal(str(unit.confidence)))
        mappings.append(SourceMappingSpec(_mapping_id(tenant_id, unit_entity.entity_id, source), tenant_id, unit_entity.entity_id, claim_id, source, authority_rank("derived_extraction"), confidence, now))
        parent_id = evidence_entity_ids.get(str(unit.source_evidence_id))
        if parent_id:
            edge_id = relationship_edge_id(tenant_id, unit_entity.entity_id, RelationshipType.DERIVED_FROM, parent_id, [source.stable_key])
            edges.append(RelationshipEdge(edge_id, tenant_id, unit_entity.entity_id, parent_id, RelationshipType.DERIVED_FROM, claim_id, confidence, authority_rank("derived_extraction"), (source,)))

    fhir_type_map = {
        "Patient": CanonicalEntityType.PATIENT,
        "Encounter": CanonicalEntityType.ENCOUNTER,
        "Coverage": CanonicalEntityType.COVERAGE,
        "Claim": CanonicalEntityType.CLAIM,
        "ExplanationOfBenefit": CanonicalEntityType.EOB,
        "DocumentReference": CanonicalEntityType.DOCUMENT,
        "Organization": CanonicalEntityType.ORGANIZATION,
        "Practitioner": CanonicalEntityType.PRACTITIONER,
    }
    for snapshot in fhir_snapshots:
        if str(getattr(snapshot, "tenant_id", "")) != tenant_id:
            continue
        resource_type = str(snapshot.resource_type)
        canonical_type = fhir_type_map.get(resource_type, CanonicalEntityType.FHIR_RESOURCE)
        # Explicit claim/patient binding allows a source version to map to an existing canonical identity.
        if resource_type == "Claim" and str(getattr(snapshot, "claim_id", "") or "") == claim_id:
            target_entity = claim_entity
        elif resource_type == "Patient" and str(getattr(snapshot, "patient_subject_id", "") or "") == patient_subject_id:
            target_entity = patient_entity
        else:
            target_entity = _entity(tenant_id, canonical_type, f"fhir:{snapshot.connection_id}:{resource_type}:{snapshot.logical_id}", claim_id=claim_id if getattr(snapshot, "claim_id", None) == claim_id else None, patient_subject_id=patient_subject_id if getattr(snapshot, "patient_subject_id", None) == patient_subject_id else None, attributes={"fhir_resource_type": resource_type, "logical_id": snapshot.logical_id})
            entities.append(target_entity)
        fhir_source = source_ref_from_fhir(snapshot, source_system=f"fhir:{snapshot.connection_id}")
        source_kind = {"Encounter": "fhir_encounter", "ExplanationOfBenefit": "fhir_eob", "Coverage": "fhir_coverage", "Claim": "fhir_claim"}.get(resource_type, "fhir_claim")
        rank = authority_rank(source_kind)
        mappings.append(SourceMappingSpec(_mapping_id(tenant_id, target_entity.entity_id, fhir_source), tenant_id, target_entity.entity_id, claim_id if getattr(snapshot, "claim_id", None) == claim_id else None, fhir_source, rank, Decimal("0.98000") if getattr(snapshot, "authoritative", False) else Decimal("0.85000"), now))
        if target_entity.entity_id not in {claim_entity.entity_id, patient_entity.entity_id} and getattr(snapshot, "claim_id", None) == claim_id:
            edge_id = relationship_edge_id(tenant_id, target_entity.entity_id, RelationshipType.SUPPORTS, claim_entity.entity_id, [fhir_source.stable_key])
            edges.append(RelationshipEdge(edge_id, tenant_id, target_entity.entity_id, claim_entity.entity_id, RelationshipType.SUPPORTS, claim_id, Decimal("0.95000"), rank, (fhir_source,)))

    # Stable IDs allow callers to insert with ON CONFLICT/lookup semantics without creating duplicates.
    unique_edges: dict[str, RelationshipEdge] = {edge.edge_id: edge for edge in edges}
    unique_mappings: dict[str, SourceMappingSpec] = {mapping.mapping_id: mapping for mapping in mappings}
    return CompiledClaimGraph(_dedupe_entities(entities), tuple(unique_mappings.values()), tuple(unique_edges.values()))
