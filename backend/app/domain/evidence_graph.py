from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256
from typing import Any, Iterable
from uuid import NAMESPACE_URL, uuid5


class CanonicalEntityType(StrEnum):
    PATIENT = "patient"
    COVERAGE = "coverage"
    POLICY = "policy"
    ENCOUNTER = "encounter"
    PRACTITIONER = "practitioner"
    ORGANIZATION = "organization"
    PROVIDER = "provider"
    CLAIM = "claim"
    CLAIM_LINE = "claim_line"
    EOB = "eob"
    DOCUMENT = "document"
    EVIDENCE = "evidence"
    EXTRACTION_UNIT = "extraction_unit"
    FHIR_RESOURCE = "fhir_resource"


class RelationshipType(StrEnum):
    SUBJECT_OF = "subject_of"
    COVERED_BY = "covered_by"
    OCCURRED_DURING = "occurred_during"
    PROVIDED_BY = "provided_by"
    BILLED_BY = "billed_by"
    PAID_BY = "paid_by"
    HAS_LINE = "has_line"
    SUPPORTS = "supports"
    DERIVED_FROM = "derived_from"
    REPRESENTS = "represents"
    REFERENCES = "references"
    CROSSWALKED_TO = "crosswalked_to"
    CONTRADICTS = "contradicts"


class TemporalAlignment(StrEnum):
    ALIGNED = "aligned"
    PARTIAL = "partial"
    OUTSIDE = "outside"
    UNKNOWN = "unknown"


class ContradictionSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    MATERIAL = "material"


@dataclass(frozen=True, slots=True)
class SourceRef:
    source_type: str
    source_system: str
    resource_type: str
    resource_id: str
    version: str | None = None
    content_sha256: str | None = None
    locator: dict[str, Any] = field(default_factory=dict)

    @property
    def stable_key(self) -> str:
        return "|".join(
            [self.source_type, self.source_system, self.resource_type, self.resource_id, self.version or ""]
        )


@dataclass(frozen=True, slots=True)
class CanonicalEntity:
    entity_id: str
    tenant_id: str
    entity_type: CanonicalEntityType
    canonical_key: str
    claim_id: str | None = None
    patient_subject_id: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)
    valid_from: date | None = None
    valid_to: date | None = None


@dataclass(frozen=True, slots=True)
class RelationshipEdge:
    edge_id: str
    tenant_id: str
    source_entity_id: str
    target_entity_id: str
    relationship_type: RelationshipType
    claim_id: str | None
    confidence: Decimal
    authority_rank: int
    provenance: tuple[SourceRef, ...]
    valid_from: date | None = None
    valid_to: date | None = None
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CodeIdentity:
    canonical_system: str
    canonical_code: str
    display: str | None = None


@dataclass(frozen=True, slots=True)
class CrosswalkScore:
    score: Decimal
    status: str
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Contradiction:
    field_name: str
    left_value: Any
    right_value: Any
    severity: ContradictionSeverity
    confidence: Decimal
    left_source: SourceRef
    right_source: SourceRef


SYSTEM_ALIASES = {
    "http://www.ama-assn.org/go/cpt": "CPT",
    "https://www.ama-assn.org/go/cpt": "CPT",
    "cpt": "CPT",
    "hcpcs": "HCPCS",
    "http://www.cms.gov/medicare/coding/hcpcsreleasecodesets": "HCPCS",
    "icd-10-cm": "ICD-10-CM",
    "http://hl7.org/fhir/sid/icd-10-cm": "ICD-10-CM",
    "icd-10-pcs": "ICD-10-PCS",
    "http://snomed.info/sct": "SNOMED-CT",
    "snomed": "SNOMED-CT",
    "loinc": "LOINC",
    "http://loinc.org": "LOINC",
    "ndc": "NDC",
    "http://hl7.org/fhir/sid/ndc": "NDC",
}

SOURCE_AUTHORITY = {
    "fhir_encounter": 95,
    "fhir_eob": 92,
    "fhir_coverage": 92,
    "fhir_claim": 88,
    "policy_system": 90,
    "accepted_original_evidence": 80,
    "structured_claim_db": 78,
    "derived_extraction": 68,
    "user_assertion": 45,
    "unknown": 25,
}


def canonical_entity_id(tenant_id: str, entity_type: CanonicalEntityType | str, canonical_key: str) -> str:
    kind = str(entity_type.value if isinstance(entity_type, CanonicalEntityType) else entity_type).lower()
    identity = f"medclaimiq://{tenant_id}/{kind}/{canonical_key.strip().lower()}"
    return f"ce_{uuid5(NAMESPACE_URL, identity).hex}"


def relationship_edge_id(
    tenant_id: str,
    source_entity_id: str,
    relationship_type: RelationshipType | str,
    target_entity_id: str,
    provenance_keys: Iterable[str] = (),
) -> str:
    relationship = relationship_type.value if isinstance(relationship_type, RelationshipType) else str(relationship_type)
    material = "|".join(
        [tenant_id, source_entity_id, relationship, target_entity_id, *sorted(provenance_keys)]
    )
    return f"edge_{sha256(material.encode()).hexdigest()[:32]}"


def normalize_code(system: str | None, code: str | None, display: str | None = None) -> CodeIdentity | None:
    if not code or not str(code).strip():
        return None
    raw_system = (system or "unknown").strip()
    canonical_system = SYSTEM_ALIASES.get(raw_system.lower(), raw_system.upper())
    canonical_code = str(code).strip().upper().replace(" ", "")
    return CodeIdentity(canonical_system=canonical_system, canonical_code=canonical_code, display=display)


def authority_rank(source_kind: str) -> int:
    return SOURCE_AUTHORITY.get(source_kind, SOURCE_AUTHORITY["unknown"])


def temporal_alignment(
    service_from: date | None,
    service_to: date | None,
    valid_from: date | None,
    valid_to: date | None,
) -> TemporalAlignment:
    if service_from is None or valid_from is None:
        return TemporalAlignment.UNKNOWN
    s_to = service_to or service_from
    v_to = valid_to or date.max
    if valid_from <= service_from and s_to <= v_to:
        return TemporalAlignment.ALIGNED
    if s_to < valid_from or v_to < service_from:
        return TemporalAlignment.OUTSIDE
    return TemporalAlignment.PARTIAL


def score_claim_line_crosswalk(
    *,
    left_code_system: str | None,
    left_code: str | None,
    left_service_date: date | None,
    left_amount: Decimal | None,
    right_code_system: str | None,
    right_code: str | None,
    right_service_date: date | None,
    right_amount: Decimal | None,
) -> CrosswalkScore:
    score = Decimal("0")
    reasons: list[str] = []
    left_identity = normalize_code(left_code_system, left_code)
    right_identity = normalize_code(right_code_system, right_code)
    if left_identity and right_identity and left_identity == right_identity:
        score += Decimal("0.55")
        reasons.append("canonical_code_match")
    elif left_identity and right_identity and left_identity.canonical_code == right_identity.canonical_code:
        score += Decimal("0.40")
        reasons.append("code_match_system_differs")

    if left_service_date and right_service_date:
        delta = abs((left_service_date - right_service_date).days)
        if delta == 0:
            score += Decimal("0.25")
            reasons.append("service_date_exact")
        elif delta <= 1:
            score += Decimal("0.15")
            reasons.append("service_date_near")

    if left_amount is not None and right_amount is not None:
        difference = abs(left_amount - right_amount)
        tolerance = max(Decimal("1.00"), abs(left_amount) * Decimal("0.01"))
        if difference == 0:
            score += Decimal("0.20")
            reasons.append("amount_exact")
        elif difference <= tolerance:
            score += Decimal("0.12")
            reasons.append("amount_within_tolerance")

    score = min(score, Decimal("1.00000"))
    status = "matched" if score >= Decimal("0.85") else "review_required" if score >= Decimal("0.60") else "unmatched"
    return CrosswalkScore(score=score, status=status, reasons=tuple(reasons))


def evidence_confidence(*, authority: int, integrity_verified: bool, extraction_confidence: Decimal | None = None, corroborating_sources: int = 0) -> Decimal:
    value = Decimal(str(max(0, min(authority, 100)))) / Decimal("100") * Decimal("0.55")
    if integrity_verified:
        value += Decimal("0.20")
    if extraction_confidence is not None:
        bounded = max(Decimal("0"), min(Decimal("1"), extraction_confidence))
        value += bounded * Decimal("0.15")
    value += min(Decimal("0.10"), Decimal(str(max(0, corroborating_sources))) * Decimal("0.025"))
    return min(Decimal("1.00000"), value.quantize(Decimal("0.00001")))


def contradiction_for_values(
    *,
    field_name: str,
    left_value: Any,
    right_value: Any,
    left_source: SourceRef,
    right_source: SourceRef,
    material_fields: set[str] | None = None,
) -> Contradiction | None:
    if left_value is None or right_value is None or left_value == right_value:
        return None
    material = material_fields or {"patient", "provider", "service_code", "service_date", "amount", "coverage_status", "prior_authorization"}
    severity = ContradictionSeverity.MATERIAL if field_name in material else ContradictionSeverity.WARNING
    confidence = Decimal("0.95") if left_source.content_sha256 and right_source.content_sha256 else Decimal("0.80")
    return Contradiction(
        field_name=field_name,
        left_value=left_value,
        right_value=right_value,
        severity=severity,
        confidence=confidence,
        left_source=left_source,
        right_source=right_source,
    )


def build_rag_metadata(
    *,
    tenant_id: str,
    claim_id: str,
    patient_subject_id: str,
    entity_ids: Iterable[str],
    relationship_types: Iterable[str] = (),
    source_ref: SourceRef,
    service_date: date | None = None,
    authority: int,
    confidence: Decimal,
    acl_tags: Iterable[str] = (),
    temporal_status: TemporalAlignment | None = None,
) -> dict[str, Any]:
    """Create the strict metadata envelope future vector/structured RAG must preserve."""
    return {
        "tenant_id": tenant_id,
        "claim_id": claim_id,
        "patient_subject_id": patient_subject_id,
        "entity_ids": sorted(set(entity_ids)),
        "relationship_types": sorted(set(relationship_types)),
        "source_type": source_ref.source_type,
        "source_system": source_ref.source_system,
        "source_resource_type": source_ref.resource_type,
        "source_resource_id": source_ref.resource_id,
        "source_version": source_ref.version,
        "source_content_sha256": source_ref.content_sha256,
        "source_locator": source_ref.locator,
        "service_date": service_date.isoformat() if service_date else None,
        "authority_rank": authority,
        "evidence_confidence": str(confidence),
        "acl_tags": sorted(set(acl_tags)),
        "temporal_alignment": temporal_status.value if temporal_status else None,
    }
