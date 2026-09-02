from decimal import Decimal
from types import SimpleNamespace

from app.domain.rag import RAGDomain
from app.rag.source_builder import document_from_extraction_units


def test_extraction_units_become_citation_aware_knowledge_document():
    unit = SimpleNamespace(
        unit_id="unit-1", text_content="Total billed amount 125.00", structured_data={"amount": "125.00"},
        unit_type="table", page_number=3, start_ms=None, end_ms=None, bbox=[1, 2, 3, 4],
        source_locator={"page": 3},
    )
    document = document_from_extraction_units(
        tenant_id="tenant-a", claim_id="claim-1", patient_subject_id="patient-1",
        source_evidence_id="ev-1", source_version="1", source_content_sha256="a" * 64,
        units=[unit], source_type="medical_invoice", authority_rank=80, evidence_confidence=Decimal("0.88"),
        entity_ids=["claim-line-entity"],
    )
    assert document.domain is RAGDomain.INVOICE
    assert document.segments[0].citation.page_number == 3
    assert document.segments[0].citation.extraction_unit_id == "unit-1"
    assert document.acl_tags == ("claim_authorized",)
