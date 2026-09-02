from __future__ import annotations
from datetime import UTC,date,datetime
from decimal import Decimal
import hashlib
from pathlib import Path
import pytest
from app.models.claims import EvidenceArtifactModel
from app.models.document_intelligence import DocumentExtractionRunModel,ExtractionUnitModel
from app.models.fhir import FHIRConnectionModel,FHIRResourceSnapshotModel
from app.services.provider_dispute_intelligence import ProviderDisputeIntelligenceService
from app.services.review_workbench import ReviewConflictError
from tests.test_appeal_evidence_reconsideration import factory
from tests.test_recovery_operations import setup_recovery,add_provider

def _sha(s):return hashlib.sha256(s.encode()).hexdigest()
def seed_dispute(db,key="p45"):
    svc,c,_=setup_recovery(db,key,Decimal("250"));add_provider(db);lease=svc.acquire_lease(c.recovery_case_id,"finance-op",expected_case_version=1)
    d=svc.submit_dispute(c.recovery_case_id,"provider-user",external_reference=f"PD-{key}",disputed_amount=Decimal("200"),currency="USD",reason_code="recovery_not_owed",statement="Provider states this recovery is not owed and submits new evidence for independent review.",evidence_refs=[],idempotency_key=f"{key}-dispute")
    now=datetime.now(UTC)
    sources=[("ev-p45-doc","application/pdf","provider_statement",{"amount":"150.00","service_code":"99213"},"Provider corrected invoice amount 150.00 and states recovery not owed."),("ev-p45-image","image/png","remittance_image",{"status":"paid","amount":"150.00"},"Image-extracted remittance amount 150.00"),("ev-p45-audio","audio/wav","provider_call",{"status":"contested"},"Provider audio transcript states no overpayment occurred.")]
    for idx,(eid,mt,dt,structured,text) in enumerate(sources,1):
        db.add(EvidenceArtifactModel(evidence_id=eid,tenant_id="tenant-a",claim_id=c.claim_id,patient_subject_id="p1",source_type="provider",source_system="provider-portal",source_locator={"provider":"org-a"},document_type=dt,media_type=mt,object_key=f"accepted/{eid}",content_sha256=hex(idx)[2:]*64 if idx<10 else "c"*64,byte_size=100+idx,status="ready",evidence_version=1,uploaded_by_user_id="provider-user",authoritative=False,media_metadata={}))
        db.add(DocumentExtractionRunModel(run_id=f"run-{eid}",tenant_id="tenant-a",claim_id=c.claim_id,evidence_id=eid,requested_by_event_id=None,media_type=mt,pipeline_version="multimodal-v3",parser_name="synthetic",parser_version="1",status="succeeded",attempt_number=1,aggregate_confidence=Decimal("0.95"),unit_count=1,warnings=[],parser_metadata={},idempotency_key=f"extract-{eid}",trace_id=None,error_code=None,error_detail=None,retryable=False,next_attempt_at=None,started_at=now,completed_at=now,derived_evidence_id=None))
        db.add(ExtractionUnitModel(unit_id=f"unit-{eid}",tenant_id="tenant-a",claim_id=c.claim_id,run_id=f"run-{eid}",source_evidence_id=eid,unit_type="text",sequence=1,text_content=text,structured_data=structured,confidence=Decimal("0.95"),page_number=1 if mt=="application/pdf" else None,start_ms=1000 if mt.startswith("audio/") else None,end_ms=5000 if mt.startswith("audio/") else None,bbox=[10,10,200,80] if mt.startswith(("application/","image/")) else None,source_locator={"kind":"provider_dispute"},citation_anchor={},content_sha256=_sha(text),created_at=now))
    if db.get(FHIRConnectionModel,"fhir-p45") is None:db.add(FHIRConnectionModel(connection_id="fhir-p45",tenant_id="tenant-a",connection_key="p45",display_name="P45 FHIR",base_url="https://fhir.invalid",fhir_version="4.0.1",auth_mode="smart_backend_services",status="active",rate_limit_per_second=Decimal("10"),max_attempts=3,config_metadata={}))
    db.flush();resource={"resourceType":"ClaimResponse","id":"cr-p45","payment":{"amount":{"value":150,"currency":"USD"}}};db.add(FHIRResourceSnapshotModel(snapshot_id="fhir-snap-p45",tenant_id="tenant-a",connection_id="fhir-p45",claim_id=c.claim_id,patient_subject_id="p1",resource_type="ClaimResponse",logical_id="cr-p45",version_id="2",last_updated=now,source_url="https://fhir.invalid/ClaimResponse/cr-p45",content_sha256=_sha(str(resource)),raw_resource=resource,canonical_resource=resource,authoritative=True,fetched_at=now));db.flush()
    intel=ProviderDisputeIntelligenceService(db,"tenant-a");intel.add_provider_agreement("finance-op",provider_organization_id="org-a",agreement_key="agreement-a",version="2026.1",title="Provider Agreement 2026",effective_from=date(2026,1,1),effective_to=date(2026,12,31),content_text="Overpayments are subject to recoupment after notice and independent dispute review. CPT 99213 follows the contracted fee schedule.",metadata={"fee_schedule":"2026"});intel.add_reimbursement_policy("finance-op",policy_key="overpayment-policy",version="2026.1",title="Overpayment Recovery Policy",effective_from=date(2026,1,1),effective_to=None,content_text="Verified overpayments may be recovered through governed recoupment. Provider disputes require evidence and independent human resolution.",metadata={})
    return svc,c,d,intel,lease

def test_secure_multimodal_reingestion_and_locked_policy_bound_snapshot():
    f=factory()
    with f() as db:
        _,c,d,intel,_=seed_dispute(db,"multi")
        modalities=[]
        for eid in ("ev-p45-doc","ev-p45-image","ev-p45-audio"):
            row=intel.process_evidence(c.recovery_case_id,d.dispute_id,eid,"provider-user");modalities.append(row.modality);assert row.status=="ready" and row.file_validation_status=="passed" and row.chunk_count==1
        fhir=intel.register_fhir(c.recovery_case_id,d.dispute_id,"fhir-snap-p45","finance-op");assert fhir.modality=="fhir" and fhir.status=="ready"
        snap=intel.build_snapshot(c.recovery_case_id,d.dispute_id,"finance-op");assert snap.status=="locked" and set(snap.modalities)=={"document","image","audio","fhir"};assert snap.recovery_evidence_pack_sha256==intel.recovery.pack(c.recovery_case_id).payload_sha256;assert {x["source_kind"] for x in snap.policy_sources}=={"provider_agreement","reimbursement_policy"}

def test_original_recovery_vs_provider_comparison_and_policy_rag_have_citation_lineage():
    f=factory()
    with f() as db:
        _,c,d,intel,_=seed_dispute(db,"rag")
        intel.process_evidence(c.recovery_case_id,d.dispute_id,"ev-p45-doc","provider-user");snap=intel.build_snapshot(c.recovery_case_id,d.dispute_id,"finance-op")
        comparisons=intel.repo.comparisons(d.dispute_id);assert any(x.comparison_type=="contradictory" and x.field.endswith("amount") for x in comparisons);assert any(x.field=="payment_policy" and x.severity=="material" for x in comparisons)
        result=intel.search(c.recovery_case_id,d.dispute_id,"finance-op","recoupment overpayment CPT 99213 provider agreement",limit=10);scopes={x.source_scope for x in result["items"]};assert "provider_evidence" in scopes and "provider_agreement" in scopes and "reimbursement_policy" in scopes;assert all(x.citation for x in result["items"]);assert result["run"].snapshot_id==snap.snapshot_id and result["run"].citation_coverage==1.0

def test_recommendation_agent_is_evidence_bound_and_stops_at_human_checkpoint():
    f=factory()
    with f() as db:
        _,c,d,intel,_=seed_dispute(db,"agent");intel.process_evidence(c.recovery_case_id,d.dispute_id,"ev-p45-doc","provider-user");intel.build_snapshot(c.recovery_case_id,d.dispute_id,"finance-op")
        run=intel.run_recommendation(c.recovery_case_id,d.dispute_id,"finance-op",idempotency_key="release45-agent-run");assert run.adjudication_authority=="none" and run.requires_human_review and run.recommendation in {"escalate","consider_reduce_recovery"};assert run.policy_refs and run.evidence_refs
        cp=intel.repo.checkpoints(d.dispute_id)[-1];assert cp.status=="waiting_human" and cp.requires_human_action and cp.state_metadata["adjudication_authority"]=="none";assert intel.recovery.disputes(c.recovery_case_id)[0].status!="resolved"

def test_missing_evidence_request_and_related_provider_response_preserve_human_resolution_boundary():
    f=factory()
    with f() as db:
        _,c,d,intel,_=seed_dispute(db,"response");req=intel.request_missing_evidence(c.recovery_case_id,d.dispute_id,"finance-op",document_types=["fee_schedule","remittance"],rationale="The effective fee schedule and remittance are required before independent human dispute resolution.",idempotency_key="release45-missing")
        resp=intel.provider_response(c.recovery_case_id,d.dispute_id,"provider-user",request_id=req.request_id,statement="Provider supplies the requested fee schedule reference and remittance for the human reviewer.",evidence_refs=["ev-p45-doc"],idempotency_key="release45-response");assert resp.body_sha256 and intel.repo.missing_requests(d.dispute_id)[0].status=="satisfied";assert intel.recovery.disputes(c.recovery_case_id)[0].status!="resolved"

def test_worker_and_agent_source_have_no_dispute_resolution_accounting_payment_or_money_calls():
    service=Path("app/services/provider_dispute_intelligence.py").read_text();worker=Path("app/workers/provider_dispute_intelligence.py").read_text();graph=Path("app/orchestration/provider_dispute_intelligence.py").read_text();forbidden=("resolve_dispute(","_post_journal(","authorize_packet(","handoff(","collect_funds(","move_money(")
    assert not any(x in service or x in worker for x in forbidden);assert '"adjudication_authority":"none"' in service;assert "independent_human_dispute_gate" in graph and '"adjudication_authority":"none"' in graph

def test_release45_traceability_points_to_release46_evidence_bound_independent_human_resolution():
    migration=Path("alembic/versions/0040_provider_dispute_intelligence.py").read_text();assert 'down_revision="0039_recovery_operations_provider_disputes"' in migration and "FORCE ROW LEVEL SECURITY" in migration and "reject_dispute_intelligence_immutable_mutation" in migration
    f=factory()
    with f() as db:
        _,c,d,intel,_=seed_dispute(db,"trace");intel.process_evidence(c.recovery_case_id,d.dispute_id,"ev-p45-doc","provider-user");intel.build_snapshot(c.recovery_case_id,d.dispute_id,"finance-op");intel.run_recommendation(c.recovery_case_id,d.dispute_id,"finance-op",idempotency_key="release45-trace-agent");trace=intel.traceability(c.recovery_case_id,d.dispute_id,"finance-op");assert trace["final_resolution_source"]=="Release 46 evidence-bound independent human dispute resolution only" and trace["authority"]["ai_resolves_dispute"] is False
