from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
import hashlib

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app import models  # noqa
from app.db.base import Base
from app.domain.claims import HumanDecision
from app.models.claims import ClaimLineModel, ClaimModel, EvidenceArtifactModel
from app.models.document_intelligence import DocumentExtractionRunModel, ExtractionUnitModel
from app.models.appeal_reconsideration import AppealEvidenceReingestionModel
from app.models.tenancy import OrganizationModel, TenantMembershipModel, TenantModel, UserAccountModel
from app.services.appeal_reconsideration import AppealReconsiderationService
from app.services.governed_closure import GovernedClosureService
from app.services.post_decision import PostDecisionService
from app.services.review_workbench import ReviewConflictError, ReviewWorkbenchService


def _sha(text:str)->str:return hashlib.sha256(text.encode()).hexdigest()


def factory():
    engine=create_engine("sqlite+pysqlite:///:memory:",future=True)
    Base.metadata.create_all(engine)
    f=sessionmaker(bind=engine,autoflush=False,expire_on_commit=False)
    with f() as db:
        db.add(TenantModel(tenant_id="tenant-a",slug="tenant-a",display_name="Tenant A",tenant_type="payer",status="active",data_region="local"))
        db.add(OrganizationModel(organization_id="org-a",tenant_id="tenant-a",slug="org-a",display_name="Org A",organization_type="payer",external_identifiers={},is_active=True))
        for uid in ("reviewer-1","reviewer-2","reviewer-3","patient-user"):
            db.add(UserAccountModel(user_id=uid,external_issuer="https://id.example",external_subject=uid,display_name=uid,status="active"))
        db.flush()
        for idx,uid in enumerate(("reviewer-1","reviewer-2","reviewer-3"),1):
            db.add(TenantMembershipModel(membership_id=f"m-{idx}",tenant_id="tenant-a",user_id=uid,role="claims_reviewer",status="active"))
        db.add(TenantMembershipModel(membership_id="m-patient",tenant_id="tenant-a",user_id="patient-user",role="patient",status="active",patient_subject_id="p1"))
        db.add(ClaimModel(claim_id="claim-1",tenant_id="tenant-a",external_claim_ref="EXT-1",patient_subject_id="p1",provider_organization_id="org-a",payer_organization_id="org-a",claim_type="medical",status="human_review",status_version=5,total_amount=Decimal("1000.00"),currency="USD",service_from=date(2026,8,1)))
        db.add(ClaimLineModel(claim_line_id="line-1",tenant_id="tenant-a",claim_id="claim-1",line_number=1,code_system="CPT",service_code="99213",description="Synthetic",service_date=date(2026,8,1),units=Decimal("1"),amount=Decimal("1000.00"),provider_id=None))
        db.add(EvidenceArtifactModel(evidence_id="ev-original",tenant_id="tenant-a",claim_id="claim-1",patient_subject_id="p1",source_type="synthetic_fixture",source_system="test",source_locator={"page":1},document_type="medical_bill",media_type="application/pdf",object_key="accepted/original.pdf",content_sha256="a"*64,byte_size=100,status="ready",evidence_version=1,authoritative=True,media_metadata={}))
        db.add(EvidenceArtifactModel(evidence_id="ev-appeal",tenant_id="tenant-a",claim_id="claim-1",patient_subject_id="p1",source_type="synthetic_fixture",source_system="appeal-test",source_locator={"page":2},document_type="medical_bill",media_type="application/pdf",object_key="accepted/appeal.pdf",content_sha256="b"*64,byte_size=120,status="ready",evidence_version=2,authoritative=True,media_metadata={}))
        now=datetime.now(UTC)
        for run_id,eid,amount in (("run-original","ev-original","1000.00"),("run-appeal","ev-appeal","700.00")):
            db.add(DocumentExtractionRunModel(run_id=run_id,tenant_id="tenant-a",claim_id="claim-1",evidence_id=eid,requested_by_event_id=None,media_type="application/pdf",pipeline_version="doc-intel-v2",parser_name="synthetic",parser_version="1",status="succeeded",attempt_number=1,aggregate_confidence=Decimal("0.98"),unit_count=1,warnings=[],parser_metadata={},idempotency_key=f"extract-{eid}",trace_id=None,error_code=None,error_detail=None,retryable=False,next_attempt_at=None,started_at=now,completed_at=now,derived_evidence_id=None))
            text=f"CPT 99213 invoice total {amount}"
            db.add(ExtractionUnitModel(unit_id=f"unit-{eid}",tenant_id="tenant-a",claim_id="claim-1",run_id=run_id,source_evidence_id=eid,unit_type="table",sequence=1,text_content=text,structured_data={"service_code":"99213","amount":amount,"provider":"org-a"},confidence=Decimal("0.98"),page_number=1,start_ms=None,end_ms=None,bbox=[10,20,200,120],source_locator={"kind":"pdf_table"},citation_anchor={},content_sha256=_sha(text),created_at=now))
        db.commit()
    return f


def close_and_appeal(db):
    _,token=ReviewWorkbenchService(db,"tenant-a").acquire_lock("claim-1","reviewer-1")
    close=GovernedClosureService(db,"tenant-a")
    packet=close.save_packet("claim-1","reviewer-1",token,decision=HumanDecision.APPROVE,rationale="Original human reviewer approved based on the locked evidence set.",reason_codes=["evidence_supports"],evidence_snapshot_ids=["ev-original"],finding_refs=[],annotation_refs=[],inconsistency_refs=[],checkpoint_refs=[],approved_amount=None,partial_line_decisions=[],ai_disagreement_reason=None,escalation_queue=None,expected_claim_status_version=5,expected_packet_version=None,idempotency_key="release38-original")
    packet=close.validate_and_lock("claim-1",packet.packet_id,"reviewer-1",token,expected_packet_version=1,idempotency_key="release38-validate")
    close.close("claim-1",packet.packet_id,"reviewer-1",token,expected_packet_version=1,expected_claim_status_version=5,idempotency_key="release38-close")
    post=PostDecisionService(db,"tenant-a");notice=post.repo.notices("claim-1")[0];post.release_notice("claim-1",notice.notice_id,"reviewer-1",idempotency_key="release38-release")
    appeal=post.submit_appeal("claim-1","patient-user","patient",notice_id=notice.notice_id,grounds=["new_evidence"],statement="The supplemental bill contains a materially different amount that should be independently reconsidered.",late_filing_reason=None,idempotency_key="release38-appeal")
    post.link_supplemental_evidence("claim-1",appeal.appeal_id,"ev-appeal","patient-user","patient",idempotency_key="release38-link")
    appeal=post.assign_appeal("claim-1",appeal.appeal_id,"reviewer-2","reviewer-3",assignment_reason="Independent reviewer assigned for supplemental evidence reconsideration.",expected_appeal_version=2,idempotency_key="release38-assign")
    appeal=post.reopen_appeal("claim-1",appeal.appeal_id,"reviewer-3",expected_appeal_version=3,rationale="Independent human reviewer reopened the appeal for evidence-bound reconsideration.",idempotency_key="release38-reopen")
    db.flush();return appeal


def test_linked_evidence_auto_registers_and_reingestion_is_version_bound():
    f=factory()
    with f() as db:
        appeal=close_and_appeal(db);svc=AppealReconsiderationService(db,"tenant-a")
        pending=db.scalar(select(AppealEvidenceReingestionModel).where(AppealEvidenceReingestionModel.appeal_id==appeal.appeal_id))
        assert pending is not None and pending.source_version=="2" and pending.status=="pending"
        row=svc.process_reingestion("claim-1",appeal.appeal_id,"ev-appeal")
        assert row.status=="ready" and row.file_validation_status=="passed"
        assert row.malware_verdict=="accepted_boundary_inherited"
        assert row.chunk_count==1 and row.embedding_model=="text-embedding-3-large"
        assert row.chunk_manifest[0]["citation"]["evidence_version"]==2


def test_locked_snapshot_preserves_original_decision_evidence_and_detects_material_changed_fact():
    f=factory()
    with f() as db:
        appeal=close_and_appeal(db);svc=AppealReconsiderationService(db,"tenant-a")
        snapshot=svc.build_snapshot("claim-1",appeal.appeal_id,"reviewer-3")
        assert snapshot.status=="locked" and snapshot.original_evidence_snapshot_sha256
        assert {x["source_id"] for x in snapshot.original_sources}=={"ev-original"}
        assert {x["source_id"] for x in snapshot.supplemental_sources}=={"ev-appeal"}
        comparisons=svc.repo.comparisons(appeal.appeal_id,snapshot.snapshot_id)
        amount=next(x for x in comparisons if x.field=="amount")
        assert amount.comparison_type=="contradictory" and amount.severity=="material"
        assert len(amount.citations)==2
        assert svc.build_snapshot("claim-1",appeal.appeal_id,"reviewer-3").snapshot_id==snapshot.snapshot_id


def test_appeal_scoped_hybrid_retrieval_and_recommendation_only_agent_have_citation_lineage():
    f=factory()
    with f() as db:
        appeal=close_and_appeal(db);svc=AppealReconsiderationService(db,"tenant-a")
        svc.build_snapshot("claim-1",appeal.appeal_id,"reviewer-3")
        result=svc.search("claim-1",appeal.appeal_id,"invoice amount CPT 99213",limit=8)
        assert result["run"].strategy=="appeal_scoped_hybrid_dense_bm25_reranked"
        assert {x.source_scope for x in result["items"]}=={"original","supplemental"}
        assert all(x.citation for x in result["items"])
        agent=svc.run_reconsideration_agent("claim-1",appeal.appeal_id)
        assert agent.adjudication_authority=="none" and agent.requires_human_review
        assert agent.recommendation=="consider_modify" and agent.contradiction_refs
        checkpoint=svc.repo.checkpoints(appeal.appeal_id)[-1]
        assert checkpoint.status=="waiting" and checkpoint.requires_human_action
        assert checkpoint.state_metadata["adjudication_authority"]=="none"


def test_independent_reviewer_annotations_checkpoint_resume_missing_evidence_and_second_level_escalation():
    f=factory()
    with f() as db:
        appeal=close_and_appeal(db);svc=AppealReconsiderationService(db,"tenant-a")
        svc.build_snapshot("claim-1",appeal.appeal_id,"reviewer-3");agent=svc.run_reconsideration_agent("claim-1",appeal.appeal_id);cp=svc.repo.checkpoints(appeal.appeal_id)[-1]
        with pytest.raises(ReviewConflictError,match="assigned"):
            svc.add_annotation("claim-1",appeal.appeal_id,"reviewer-2",target_type="recommendation",target_id=agent.reconsideration_run_id,body="Not the assigned appeal reviewer.",anchor={},tags=[],idempotency_key="bad-annotation")
        ann=svc.add_annotation("claim-1",appeal.appeal_id,"reviewer-3",target_type="recommendation",target_id=agent.reconsideration_run_id,body="Reviewed the material amount conflict against the supplemental invoice.",anchor={"comparison":"amount"},tags=["material-change"],idempotency_key="good-annotation")
        assert len(ann.body_sha256)==64
        resumed=svc.resume_checkpoint("claim-1",appeal.appeal_id,cp.checkpoint_id,"reviewer-3");assert resumed.status=="resumed"
        req=svc.request_missing_evidence("claim-1",appeal.appeal_id,"reviewer-3",document_types=["itemized_bill"],rationale="The changed amount requires the complete itemized bill before final human resolution.")
        esc=svc.escalate("claim-1",appeal.appeal_id,"reviewer-3",reason="Material amount conflict remains unresolved after comparison and requires second-level human review.")
        assert req.status=="open" and esc.level=="second_level" and esc.assigned_queue=="appeal_second_level"


def test_traceability_ends_only_in_human_resolution_and_agent_service_has_no_adjudication_calls():
    f=factory()
    with f() as db:
        appeal=close_and_appeal(db);svc=AppealReconsiderationService(db,"tenant-a")
        svc.build_snapshot("claim-1",appeal.appeal_id,"reviewer-3");svc.run_reconsideration_agent("claim-1",appeal.appeal_id)
        trace=svc.traceability("claim-1",appeal.appeal_id)
        assert trace["complete_lineage"] and trace["original_decision_immutable"] and trace["final_resolution_human_only"]
        assert trace["recommendation_agent_adjudication_authority"] is False
    service=Path("app/services/appeal_reconsideration.py").read_text();graph=Path("app/orchestration/appeal_reconsideration.py").read_text()
    forbidden=("resolve_appeal(","GovernedClosureService(","record_human_decision(","HumanReviewDecisionModel(")
    assert not any(token in service or token in graph for token in forbidden)
    assert '"adjudication_authority":"none"' in graph or '"adjudication_authority": "none"' in graph


def test_release38_migration_model_api_frontend_and_eval_dataset_contracts():
    migration=Path("alembic/versions/0033_appeal_evidence_reconsideration.py").read_text()
    assert 'down_revision="0032_communication_delivery_compliance"' in migration
    assert "FORCE ROW LEVEL SECURITY" in migration and "appeal_evidence_snapshot_payload_immutable" in migration
    assert "appeal_reconsideration_runs_immutable" in migration and "appeal_reviewer_annotations_immutable" in migration
    model=Path("app/domain/appeal_reconsideration.py").read_text();main=Path("app/main.py").read_text()
    assert "authorized_independent_human_required" in model and "llm_can_affirm_modify_or_overturn" in model
    assert "appeal_reconsideration_router" in main and "appeal-reconsideration-model" in main
    dataset=Path("../sample-data/evaluation/appeal_reconsideration_cases.jsonl").read_text().strip().splitlines()
    assert len(dataset)>=5 and all('"requires_human_resolution": true' in line for line in dataset)
    frontend=Path("../frontend/app/review/appeals/page.tsx").read_text()
    assert "Independent Appeal Review" in frontend and "Recommendation only" in frontend


def test_release38_reviewer_mutations_are_idempotent_and_original_chunk_versions_are_evidence_versions():
    f=factory()
    with f() as db:
        appeal=close_and_appeal(db);svc=AppealReconsiderationService(db,"tenant-a")
        svc.build_snapshot("claim-1",appeal.appeal_id,"reviewer-3")
        first=svc.run_reconsideration_agent("claim-1",appeal.appeal_id,idempotency_key="release38-agent-idempotent")
        second=svc.run_reconsideration_agent("claim-1",appeal.appeal_id,idempotency_key="release38-agent-idempotent")
        assert first.reconsideration_run_id==second.reconsideration_run_id
        rag=svc.repo.rag_items(first.rag_run_id)
        original=next(x for x in rag if x.source_scope=="original")
        assert original.source_version=="1" and original.citation["evidence_version"]==1
        before=appeal.appeal_version
        req1=svc.request_missing_evidence("claim-1",appeal.appeal_id,"reviewer-3",document_types=["itemized_bill"],rationale="Need complete itemization for the changed amount before human resolution.",idempotency_key="release38-missing-idem")
        req2=svc.request_missing_evidence("claim-1",appeal.appeal_id,"reviewer-3",document_types=["itemized_bill"],rationale="Need complete itemization for the changed amount before human resolution.",idempotency_key="release38-missing-idem")
        assert req1.request_id==req2.request_id and appeal.appeal_version==before+1
        esc1=svc.escalate("claim-1",appeal.appeal_id,"reviewer-3",reason="Material contradiction requires independent second-level review before resolution.",idempotency_key="release38-escalate-idem")
        esc2=svc.escalate("claim-1",appeal.appeal_id,"reviewer-3",reason="Material contradiction requires independent second-level review before resolution.",idempotency_key="release38-escalate-idem")
        assert esc1.escalation_id==esc2.escalation_id
