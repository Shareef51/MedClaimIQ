from datetime import date
from decimal import Decimal

from app.domain.evidence_graph import (
    CanonicalEntityType,
    RelationshipType,
    SourceRef,
    TemporalAlignment,
    authority_rank,
    build_rag_metadata,
    canonical_entity_id,
    contradiction_for_values,
    evidence_confidence,
    normalize_code,
    relationship_edge_id,
    score_claim_line_crosswalk,
    temporal_alignment,
)


def test_canonical_ids_are_deterministic_and_tenant_scoped():
    first = canonical_entity_id("tenant-a", CanonicalEntityType.CLAIM, "claim-001")
    assert first == canonical_entity_id("tenant-a", "claim", "claim-001")
    assert first != canonical_entity_id("tenant-b", "claim", "claim-001")


def test_code_system_aliases_normalize_cpt():
    code = normalize_code("http://www.ama-assn.org/go/cpt", " 99213 ")
    assert code is not None
    assert code.canonical_system == "CPT"
    assert code.canonical_code == "99213"


def test_temporal_alignment_exact_and_outside():
    assert temporal_alignment(date(2026, 8, 10), None, date(2026, 1, 1), date(2026, 12, 31)) == TemporalAlignment.ALIGNED
    assert temporal_alignment(date(2027, 1, 1), None, date(2026, 1, 1), date(2026, 12, 31)) == TemporalAlignment.OUTSIDE


def test_temporal_alignment_partial_window():
    assert temporal_alignment(date(2026, 12, 30), date(2027, 1, 2), date(2026, 1, 1), date(2026, 12, 31)) == TemporalAlignment.PARTIAL


def test_claim_line_crosswalk_high_confidence_match():
    result = score_claim_line_crosswalk(
        left_code_system="CPT", left_code="99213", left_service_date=date(2026, 8, 10), left_amount=Decimal("150.00"),
        right_code_system="http://www.ama-assn.org/go/cpt", right_code="99213", right_service_date=date(2026, 8, 10), right_amount=Decimal("150.00"),
    )
    assert result.score == Decimal("1.00000")
    assert result.status == "matched"


def test_claim_line_crosswalk_ambiguous_candidate_requires_review():
    result = score_claim_line_crosswalk(
        left_code_system="CPT", left_code="99213", left_service_date=date(2026, 8, 10), left_amount=Decimal("150.00"),
        right_code_system="CPT", right_code="99213", right_service_date=date(2026, 8, 15), right_amount=Decimal("125.00"),
    )
    assert result.score == Decimal("0.55")
    assert result.status == "unmatched"


def test_evidence_confidence_uses_authority_integrity_extraction_and_corroboration():
    score = evidence_confidence(authority=92, integrity_verified=True, extraction_confidence=Decimal("0.90"), corroborating_sources=2)
    assert Decimal("0.85") < score <= Decimal("1")


def test_material_contradiction_preserves_both_sources():
    left = SourceRef("structured", "medclaimiq", "Claim", "claim-1", "3", "a" * 64)
    right = SourceRef("fhir", "hospital", "ExplanationOfBenefit", "eob-1", "1", "b" * 64)
    contradiction = contradiction_for_values(field_name="amount", left_value="150.00", right_value="125.00", left_source=left, right_source=right)
    assert contradiction is not None
    assert contradiction.severity.value == "material"
    assert contradiction.left_source.resource_id == "claim-1"
    assert contradiction.right_source.resource_id == "eob-1"


def test_equal_values_do_not_create_contradiction():
    left = SourceRef("structured", "medclaimiq", "Claim", "claim-1")
    right = SourceRef("fhir", "hospital", "Claim", "fhir-claim-1")
    assert contradiction_for_values(field_name="currency", left_value="USD", right_value="USD", left_source=left, right_source=right) is None


def test_relationship_edge_id_changes_with_tenant():
    first = relationship_edge_id("tenant-a", "a", RelationshipType.SUPPORTS, "b", ["prov"])
    assert first != relationship_edge_id("tenant-b", "a", RelationshipType.SUPPORTS, "b", ["prov"])


def test_rag_metadata_has_security_and_provenance_fields():
    source = SourceRef("fhir", "hospital", "Encounter", "enc-1", "2", "a" * 64, {"snapshot_id": "snap-1"})
    metadata = build_rag_metadata(
        tenant_id="tenant-a", claim_id="claim-1", patient_subject_id="patient-1",
        entity_ids=["ce-2", "ce-1", "ce-1"], relationship_types=["supports"], source_ref=source,
        service_date=date(2026, 8, 10), authority=95, confidence=Decimal("0.95000"),
        acl_tags=["claim:read", "claim:read"], temporal_status=TemporalAlignment.ALIGNED,
    )
    assert metadata["tenant_id"] == "tenant-a"
    assert metadata["entity_ids"] == ["ce-1", "ce-2"]
    assert metadata["source_version"] == "2"
    assert metadata["acl_tags"] == ["claim:read"]
    assert metadata["temporal_alignment"] == "aligned"


def test_source_authority_has_conservative_unknown_default():
    assert authority_rank("fhir_encounter") > authority_rank("derived_extraction") > authority_rank("unknown")

from types import SimpleNamespace
from datetime import datetime, timezone
from app.services.evidence_graph import compile_claim_graph


def test_compile_claim_graph_connects_claim_line_evidence_extraction_and_fhir():
    claim = SimpleNamespace(
        tenant_id="tenant-a", claim_id="claim-1", patient_subject_id="patient-1",
        provider_organization_id="org-provider", payer_organization_id="org-payer",
        policy_id="policy-1", encounter_id="encounter-1", external_claim_ref="EXT-1",
        claim_type="medical", status_version=2, service_from=date(2026, 8, 10), service_to=None,
    )
    line = SimpleNamespace(
        tenant_id="tenant-a", claim_id="claim-1", claim_line_id="line-1", line_number=1,
        code_system="CPT", service_code="99213", amount=Decimal("150.00"), units=Decimal("1"), service_date=date(2026, 8, 10),
    )
    evidence = SimpleNamespace(
        tenant_id="tenant-a", claim_id="claim-1", evidence_id="ev-1", patient_subject_id="patient-1",
        document_type="medical_bill", media_type="application/pdf", status="accepted", source_type="upload",
        source_system="patient_portal", evidence_version=1, content_sha256="a"*64, source_locator={"page": 1}, verified_at=datetime.now(timezone.utc),
    )
    unit = SimpleNamespace(
        tenant_id="tenant-a", claim_id="claim-1", unit_id="unit-1", source_evidence_id="ev-1",
        unit_type="text", page_number=1, start_ms=None, end_ms=None, content_sha256="b"*64,
        citation_anchor={"page": 1}, source_locator={}, confidence=Decimal("0.92"),
    )
    fhir = SimpleNamespace(
        snapshot_id="snap-1", tenant_id="tenant-a", connection_id="hospital-1", claim_id="claim-1",
        patient_subject_id="patient-1", resource_type="ExplanationOfBenefit", logical_id="eob-1", version_id="1",
        content_sha256="c"*64, source_url="https://hospital.invalid/fhir/ExplanationOfBenefit/eob-1", authoritative=True,
    )
    compiled = compile_claim_graph(claim=claim, claim_lines=[line], evidence_artifacts=[evidence], extraction_units=[unit], fhir_snapshots=[fhir])
    types = {entity.entity_type.value for entity in compiled.entities}
    relationships = {edge.relationship_type.value for edge in compiled.edges}
    assert {"patient", "claim", "claim_line", "evidence", "extraction_unit", "eob"}.issubset(types)
    assert {"has_line", "supports", "derived_from", "covered_by", "occurred_during"}.issubset(relationships)
    assert any(mapping.source_ref.resource_type == "ExplanationOfBenefit" for mapping in compiled.source_mappings)


def test_compile_claim_graph_ignores_cross_tenant_fhir_snapshot():
    claim = SimpleNamespace(
        tenant_id="tenant-a", claim_id="claim-1", patient_subject_id="patient-1",
        provider_organization_id="org-provider", payer_organization_id="org-payer", policy_id=None,
        encounter_id=None, external_claim_ref="EXT-1", claim_type="medical", status_version=1,
        service_from=date(2026, 8, 10), service_to=None,
    )
    cross_tenant = SimpleNamespace(
        snapshot_id="snap-x", tenant_id="tenant-b", connection_id="hospital-x", claim_id="claim-1",
        patient_subject_id="patient-1", resource_type="Claim", logical_id="claim-x", version_id="1",
        content_sha256="d"*64, source_url="https://other.invalid/fhir/Claim/claim-x", authoritative=True,
    )
    compiled = compile_claim_graph(claim=claim, fhir_snapshots=[cross_tenant])
    assert all("hospital-x" not in mapping.source_ref.source_system for mapping in compiled.source_mappings)
