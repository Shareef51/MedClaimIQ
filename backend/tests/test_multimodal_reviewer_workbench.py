from __future__ import annotations
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
import hashlib
import fitz
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app import models  # noqa
from app.db.base import Base
from app.models.claims import ClaimModel, EvidenceArtifactModel
from app.models.multimodal_rag import MultimodalEvidencePackModel, MultimodalRAGItemModel, MultimodalRAGRunModel
from app.models.multimodal_review import MultimodalReviewAnnotationModel
from app.models.tenancy import OrganizationModel, TenantMembershipModel, TenantModel, UserAccountModel
from app.services.multimodal_review import MultimodalReviewService
from app.services.review_workbench import ReviewWorkbenchService


def factory():
    engine=create_engine("sqlite+pysqlite:///:memory:",future=True)
    Base.metadata.create_all(engine)
    f=sessionmaker(bind=engine,autoflush=False,expire_on_commit=False)
    with f() as db:
        db.add(TenantModel(tenant_id="tenant-a",slug="tenant-a",display_name="Tenant A",tenant_type="payer",status="active",data_region="local"))
        db.add(OrganizationModel(organization_id="org-a",tenant_id="tenant-a",slug="org-a",display_name="Org A",organization_type="payer",external_identifiers={},is_active=True))
        db.add(UserAccountModel(user_id="reviewer-1",external_issuer="https://id.example",external_subject="reviewer-1",display_name="Reviewer",status="active"))
        db.flush(); db.add(TenantMembershipModel(membership_id="m-1",tenant_id="tenant-a",user_id="reviewer-1",role="claims_reviewer",status="active"))
        db.add(ClaimModel(claim_id="claim-1",tenant_id="tenant-a",external_claim_ref="EXT-1",patient_subject_id="p1",provider_organization_id="org-a",payer_organization_id="org-a",claim_type="medical",status="human_review",status_version=4,total_amount=Decimal("150"),currency="USD",service_from=date(2026,8,1)))
        db.add(EvidenceArtifactModel(evidence_id="ev-1",tenant_id="tenant-a",claim_id="claim-1",patient_subject_id="p1",source_type="synthetic",source_system="fixture",source_locator={"page":1},document_type="invoice",media_type="application/pdf",object_key="accepted/ev-1.pdf",content_sha256="a"*64,byte_size=1024,status="ready",evidence_version=1,authoritative=True,media_metadata={}))
        db.add(MultimodalRAGRunModel(run_id="mmrun-1",tenant_id="tenant-a",claim_id="claim-1",query_sha256="b"*64,query_length=8,agent_name="invoice_verification",intent="invoice_verification",requested_modalities=["table","fhir"],routed_modalities=["table","fhir"],required_modalities=["table"],selected_count=1,confidence=.9,modality_coverage=1,citation_coverage=1,source_diversity=1,inconsistency_count=0,knowledge_gap_count=0,answerability="answerable",planner_version="v1",reranker_version="v1",verifier_version="v1",latency_ms=20,trace_id="trace"))
        db.add(MultimodalEvidencePackModel(pack_id="mmpack-1",tenant_id="tenant-a",claim_id="claim-1",run_id="mmrun-1",item_count=1,modalities=["table"],confidence=.9,modality_coverage=1,citation_coverage=1,answerability="answerable",pack_sha256="c"*64,created_at=datetime.now(UTC)))
        db.add(MultimodalRAGItemModel(item_event_id="mmi-evt-1",tenant_id="tenant-a",claim_id="claim-1",run_id="mmrun-1",pack_id="mmpack-1",item_id="table-1",modality="table",domain="invoice",source_id="ev-1",source_version="1",content_sha256="d"*64,rank=1,score=.9,confidence=.9,authority_rank=80,citation={"evidence_id":"ev-1","page_number":1,"bbox":[10,20,200,100]},metadata_summary={"page_width":612,"page_height":792},retrieval_sources=["multimodal"],created_at=datetime.now(UTC)))
        db.commit()
    return f


def test_snapshot_exposes_multimodal_pack_and_traceable_item():
    f=factory()
    with f() as db:
        snap=MultimodalReviewService(db,"tenant-a").snapshot("claim-1")
        assert snap["latest_pack"]["pack_id"]=="mmpack-1"
        assert snap["items"][0]["evidence_key"]=="mm:table-1"
        assert snap["items"][0]["citation"]["bbox"]==[10,20,200,100]
        assert snap["traceability"]["final_decision_human_only"] is True


def test_annotation_requires_lease_and_is_immutable_audit_input():
    f=factory()
    with f() as db:
        _,token=ReviewWorkbenchService(db,"tenant-a").acquire_lock("claim-1","reviewer-1")
        row=MultimodalReviewService(db,"tenant-a").add_annotation("claim-1","reviewer-1",token,target_type="multimodal_item",target_id="table-1",annotation_kind="highlight",anchor={"page_number":1,"bbox":[10,20,200,100]},body="Verify this invoice line against FHIR EOB.",tags=["invoice"],idempotency_key="annotation-12345")
        db.commit()
        assert row.body_sha256==hashlib.sha256(b"Verify this invoice line against FHIR EOB.").hexdigest()
        persisted=db.scalar(select(MultimodalReviewAnnotationModel).where(MultimodalReviewAnnotationModel.annotation_id==row.annotation_id))
        assert persisted.target_id=="table-1" and persisted.anchor["page_number"]==1


class FakeStorage:
    def __init__(self, payload:bytes): self.payload=payload
    def iter_object_chunks(self, *, bucket:str, key:str, chunk_size:int=1024*1024): yield self.payload
    def create_presigned_download(self, *, bucket:str, key:str, expires_seconds:int, response_content_type:str|None=None): return "https://signed.invalid/object"


def test_pdf_page_preview_renders_highlighted_png():
    doc=fitz.open(); page=doc.new_page(width=300,height=400); page.insert_text((20,40),"Synthetic invoice evidence"); raw=doc.tobytes(); doc.close()
    f=factory()
    with f() as db:
        db.scalar(select(EvidenceArtifactModel).where(EvidenceArtifactModel.evidence_id=="ev-1")).byte_size=len(raw)
        png=MultimodalReviewService(db,"tenant-a").render_pdf_page("claim-1","ev-1",storage=FakeStorage(raw),bucket_name="medclaimiq",page_number=1,bbox=[10,20,200,100])
        assert png.startswith(b"\x89PNG") and len(png)>500


def test_signed_access_hides_object_key_from_response():
    f=factory()
    with f() as db:
        response=MultimodalReviewService(db,"tenant-a").evidence_access("claim-1","ev-1",storage=FakeStorage(b"x"),bucket_name="medclaimiq")
        assert response["url"].startswith("https://signed.invalid")
        assert "object_key" not in response


def test_migration_forces_rls_and_immutable_annotations():
    text=Path("alembic/versions/0029_multimodal_reviewer_workbench.py").read_text()
    assert "FORCE ROW LEVEL SECURITY" in text
    assert "multimodal_review_annotations_immutable" in text
    assert "body_sha256" in text and "idempotency_key" in text
