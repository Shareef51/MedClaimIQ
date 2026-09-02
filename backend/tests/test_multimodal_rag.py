from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.document_intelligence.processors import VideoProcessor
from app.domain.advanced_rag import Answerability
from app.domain.multimodal_rag import EvidenceModality, InconsistencySeverity, MultimodalCitation
from app.domain.rag import RAGDomain, RetrievalScope
from app.main import app
from app.rag.multimodal_routing import MultimodalRouter
from app.rag.multimodal_verification import CrossModalVerifier
from app.repositories.multimodal_rag import ExtractionSourceUnit
from app.schemas.multimodal_rag import MultimodalRAGRequest
from app.services.multimodal_rag import MultimodalRAGService

ROOT = Path(__file__).resolve().parents[2]


def _unit(*, unit_id: str, unit_type: str, text: str | None, evidence: str, confidence: float = .95, page=1, bbox=None, start=None, end=None, locator=None, structured=None):
    return SimpleNamespace(
        unit_id=unit_id, unit_type=unit_type, text_content=text, structured_data=structured or {},
        source_evidence_id=evidence, confidence=confidence, page_number=page, bbox=bbox,
        start_ms=start, end_ms=end, source_locator=locator or {},
    )


class _Repo:
    tenant_id = "tenant-1"
    def __init__(self, units=(), fhir=()):
        self.units=list(units); self.fhir=list(fhir); self.persisted=None
    def extraction_units(self, *, claim_id): return self.units
    def fhir_snapshots(self, *, claim_id): return self.fhir
    def add_result(self, **kwargs): self.persisted=kwargs


def _scope():
    return RetrievalScope(tenant_id="tenant-1", claim_id="claim-1", patient_subject_id="patient-1", domains=(RAGDomain.EVIDENCE,RAGDomain.INVOICE,RAGDomain.HOSPITAL), acl_tags=("claim_authorized","user:u1"))


def test_multimodal_router_detects_video_and_fhir_cross_modal_intent():
    route=MultimodalRouter().plan("Compare video keyframe timeline with hospital FHIR record")
    assert EvidenceModality.VIDEO in route.modalities
    assert EvidenceModality.FHIR in route.modalities
    assert route.intent.value == "cross_modal_verification"


def test_required_modalities_cannot_escape_explicit_requested_modalities():
    with pytest.raises(ValueError, match="subset"):
        MultimodalRAGRequest(query="verify", modalities=(EvidenceModality.IMAGE,), required_modalities=(EvidenceModality.VIDEO,))


def test_multimodal_citations_require_timecode_and_frame_anchor():
    audio=MultimodalCitation(modality=EvidenceModality.AUDIO,evidence_id="ev")
    assert audio.validate()[0] is False
    video=MultimodalCitation(modality=EvidenceModality.VIDEO,evidence_id="ev",start_ms=15000,end_ms=15000,source_locator={"kind":"keyframe"})
    assert "missing_frame_index" in video.validate()[1]
    valid=MultimodalCitation(modality=EvidenceModality.VIDEO,evidence_id="ev",start_ms=15000,end_ms=15000,frame_index=1,frame_sha256="a"*64,source_locator={"kind":"keyframe"})
    assert valid.validate()[0]


def test_cross_modal_verifier_detects_material_amount_mismatch():
    from app.domain.multimodal_rag import MultimodalCandidate
    left=MultimodalCandidate("i1",EvidenceModality.TABLE,RAGDomain.INVOICE,"ev1","v1","Total $150.00",.9,.9,80,MultimodalCitation(EvidenceModality.TABLE,evidence_id="ev1",page_number=1,source_locator={"table":0}))
    right=MultimodalCandidate("i2",EvidenceModality.FHIR,RAGDomain.HOSPITAL,"ExplanationOfBenefit/e1","3","EOB total $125.00",.9,.95,95,MultimodalCitation(EvidenceModality.FHIR,fhir_snapshot_id="s1",fhir_resource_type="ExplanationOfBenefit",fhir_logical_id="e1",fhir_version_id="3"))
    mismatches=CrossModalVerifier().verify([left,right])
    assert any(x.field == "amount" and x.severity == InconsistencySeverity.MATERIAL for x in mismatches)


def test_multimodal_service_builds_pack_and_blocks_material_conflict():
    img=ExtractionSourceUnit(_unit(unit_id="img1",unit_type="image",text="Scanned invoice total $150.00",evidence="ev-img",bbox=[1,2,100,50],locator={"kind":"image_ocr"}),"image/png","document-intelligence-v1")
    table=ExtractionSourceUnit(_unit(unit_id="tbl1",unit_type="table",text="Invoice total $125.00",evidence="ev-pdf",page=2,locator={"table":0}),"application/pdf","document-intelligence-v1")
    repo=_Repo([img,table])
    result=MultimodalRAGService(repository=repo,text_retriever=None).search(
        query="Compare invoice image and table amount",scope=_scope(),requested_modalities=(EvidenceModality.IMAGE,EvidenceModality.TABLE),required_modalities=(EvidenceModality.IMAGE,EvidenceModality.TABLE),limit=8,
    )
    assert {x.modality for x in result.pack.items} == {EvidenceModality.IMAGE,EvidenceModality.TABLE}
    assert any(x.severity == InconsistencySeverity.MATERIAL for x in result.pack.inconsistencies)
    assert result.pack.answerability == Answerability.INSUFFICIENT
    assert repo.persisted is not None
    assert repo.persisted["run"].query_sha256 and len(repo.persisted["run"].query_sha256)==64
    assert all(len(x.content_sha256)==64 for x in repo.persisted["items"])


def test_multimodal_service_preserves_authoritative_scope_for_text_retrieval():
    class Text:
        def __init__(self): self.scope=None
        def search(self, **kwargs): self.scope=kwargs["scope"]; return SimpleNamespace(hits=())
    text=Text(); repo=_Repo()
    MultimodalRAGService(repository=repo,text_retriever=text).search(query="claim evidence",scope=_scope(),requested_modalities=(EvidenceModality.TEXT,),limit=2)
    assert text.scope.tenant_id == "tenant-1"
    assert text.scope.claim_id == "claim-1"
    assert text.scope.acl_tags == ("claim_authorized","user:u1")


def test_video_processor_preserves_frame_index_hash_and_timecode():
    analyzer=lambda path: {"segments":[],"keyframes":[{"timestamp_ms":15000,"frame_index":7,"frame_sha256":"b"*64,"byte_size":20,"confidence":1.0,"text":"synthetic frame"}]}
    bundle=VideoProcessor(analyzer=analyzer).parse(Path("unused.mp4"),evidence_id="ev-video",media_type="video/mp4")
    unit=bundle.units[0]
    assert unit.citation.frame_index == 7
    assert unit.citation.frame_sha256 == "b"*64
    assert unit.citation.start_ms == 15000
    assert unit.citation.source_locator["kind"] == "keyframe"


def test_multimodal_model_api_is_public_but_search_remains_internal():
    client=TestClient(app)
    r=client.get("/api/v1/multimodal-rag-model")
    assert r.status_code==200 and r.json()["architecture"]=="governed-cross-modal-rag"
    protected=client.post("/api/v1/claims/claim-1/rag/multimodal-search",json={"query":"verify image"})
    assert protected.status_code==401


def test_multimodal_migration_forces_rls_and_immutable_evidence_history():
    migration=(ROOT/"backend/alembic/versions/0027_multimodal_rag.py").read_text()
    for table in ("multimodal_rag_runs","multimodal_evidence_packs","multimodal_rag_items","multimodal_inconsistencies"):
        assert table in migration
    assert "FORCE ROW LEVEL SECURITY" in migration
    assert "medclaimiq_reject_immutable_change" in migration


def test_multimodal_release_gate_is_required():
    policy=json.loads((ROOT/"config/release_engineering_policy.json").read_text())
    assert "multimodal-rag-quality" in policy["gates"]["required"]
    promotion=(ROOT/".github/workflows/release-promotion.yml").read_text()
    assert "--gate multimodal-rag-quality=pass" in promotion


def test_multimodal_evaluation_workflow_and_dataset_exist():
    dataset=json.loads((ROOT/"sample-data/multimodal_rag_eval_v1.json").read_text())
    assert dataset["dataset_version"]=="multimodal-rag-v1"
    assert len(dataset["cases"])>=5
    workflow=(ROOT/".github/workflows/multimodal-rag-quality-gate.yml").read_text()
    assert "run_multimodal_rag_evaluations.py --gate" in workflow


def test_multimodal_telemetry_never_persists_raw_media_columns():
    models=(ROOT/"backend/app/models/multimodal_rag.py").read_text().lower()
    assert "raw_image" not in models and "raw_video" not in models and "media_bytes" not in models
    assert "content_sha256" in models and "citation" in models
