from __future__ import annotations
from datetime import UTC,datetime,timedelta
from pathlib import Path
import pytest
from app.models.tenancy import UserAccountModel,TenantMembershipModel
from app.services.regulatory_examination import RegulatoryExaminationService
from app.services.regulatory_supervisory_control import RegulatorySupervisoryControlService
from app.services.regulatory_remediation import RegulatoryRemediationService
from app.services.review_workbench import ReviewConflictError
from tests.test_recovery_control_assurance import factory
from tests.test_regulatory_supervisory_control import accepted_fixture


def examination_fixture(db,key="p52"):
    _,_,_,_,_,_,tx=accepted_fixture(db,key)
    sup=RegulatorySupervisoryControlService(db,"tenant-a");sup.refresh_cases(transmission_id=tx.transmission_id);sc=sup.repo.case_for_transmission(tx.transmission_id)
    att=sup.prepare_attestation(sc.case_id,"acct-controller",expected_case_version=sc.case_version);sc=sup.repo.case(sc.case_id)
    sup.certify(sc.case_id,att.attestation_id,"auditor-user",conclusion="reconciled",rationale="Independent human supervisor certifies the filing, release, transmission and cryptographic acknowledgment before the regulatory examination opens.",expected_case_version=sc.case_version)
    if db.get(UserAccountModel,"reg-supervisor") is None:
        db.add(UserAccountModel(user_id="reg-supervisor",external_issuer="https://id.example",external_subject="reg-supervisor",display_name="Regulatory Supervisor",status="active"));db.flush();db.add(TenantMembershipModel(membership_id=f"m-reg-supervisor-{key}",tenant_id="tenant-a",user_id="reg-supervisor",role="tenant_admin",status="active"));db.flush()
    svc=RegulatoryExaminationService(db,"tenant-a")
    case=svc.open_inquiry("acct-controller",supervisory_case_id=sc.case_id,external_inquiry_reference=f"REG-EXAM-{key}",inquiry_type="examination",question_classification="accounting_tieout",inquiry_summary="Regulator requests the certified recovery accounting tie-out, submission evidence, and explanation of the supervisory controls.",response_due_at=datetime.now(UTC)+timedelta(days=14))
    return svc,case,sc


def test_immutable_evidence_pack_and_cited_financial_accounting_rag_retrieval():
    f=factory()
    with f() as db:
        svc,case,_=examination_fixture(db,"evidence52")
        req=svc.add_document_request(case.examination_case_id,"acct-controller",request_code="ledger-tieout",description="Provide the ledger and recovery tie-out evidence supporting the certified regulatory filing.",due_at=datetime.now(UTC)+timedelta(days=7),requested_refs=[{"type":"ledger","id":"journal-source"}])
        case=svc.repo.case(case.examination_case_id);svc.satisfy_document_request(case.examination_case_id,"ledger-tieout","acct-controller",satisfied_refs=[{"type":"ledger_journal","id":"journal-source","sha256":"a"*64}],expected_case_version=case.case_version)
        case=svc.repo.case(case.examination_case_id);pack=svc.build_evidence_pack(case.examination_case_id,"acct-controller",expected_case_version=case.case_version)
        assert len(pack.payload_sha256)==64 and pack.locked_at and {x["source_type"] for x in pack.citations}>={"release49_certified_package","release50_transport_ack","release51_supervisory_trace"}
        result=svc.search_evidence(case.examination_case_id,"auditor-user","ledger accounting recovery transmission acknowledgment",top_k=8)
        assert result["results"] and all(x["citation"] for x in result["results"]) and result["financial_accounting_sources_read_only"] is True


def test_ai_assisted_response_is_draft_only_and_requires_different_human_checker_before_secure_delivery():
    f=factory()
    with f() as db:
        svc,case,_=examination_fixture(db,"response52");pack=svc.build_evidence_pack(case.examination_case_id,"acct-controller",expected_case_version=case.case_version);case=svc.repo.case(case.examination_case_id)
        draft=svc.draft_response(case.examination_case_id,"auditor-user",response_text=None,cited_refs=pack.citations[:3],use_ai_assistance=True,idempotency_key="response52-draft",expected_case_version=case.case_version)
        assert draft.status=="draft" and draft.ai_assisted is True and draft.ai_metadata["authority"]=="none" and draft.approved_by_user_id is None
        case=svc.repo.case(case.examination_case_id)
        with pytest.raises(ReviewConflictError,match="maker and checker"):svc.approve_response(case.examination_case_id,draft.response_id,"auditor-user",approval_rationale="The response maker cannot approve their own regulator response under maker-checker controls.",expected_case_version=case.case_version)
        approved=svc.approve_response(case.examination_case_id,draft.response_id,"reg-supervisor",approval_rationale="Independent human regulatory checker verifies the cited evidence and approves this regulator response for secure delivery.",expected_case_version=case.case_version)
        case=svc.repo.case(case.examination_case_id);corr=svc.deliver_response(case.examination_case_id,approved.response_id,"reg-supervisor",channel="regulator_portal",subject="Response to examination inquiry",external_reference="REG-CORR-52",supplemental_submission_reference="SUP-52-1",idempotency_key="response52-delivery",expected_case_version=case.case_version)
        assert corr.delivered is True and corr.supplemental_submission_reference=="SUP-52-1" and svc.repo.response(draft.response_id).status=="sent"


def test_open_document_requests_material_findings_and_remediation_commitments_block_human_closure():
    f=factory()
    with f() as db:
        svc,case,_=examination_fixture(db,"closure52");svc.add_document_request(case.examination_case_id,"acct-controller",request_code="supporting-doc",description="Provide supporting accounting control evidence requested by the regulator.",due_at=datetime.now(UTC)+timedelta(days=3),requested_refs=[])
        case=svc.repo.case(case.examination_case_id);pack=svc.build_evidence_pack(case.examination_case_id,"acct-controller",expected_case_version=case.case_version);case=svc.repo.case(case.examination_case_id)
        draft=svc.draft_response(case.examination_case_id,"acct-controller",response_text="The certified recovery filing and supervisory tie-outs are attached with exact cited evidence for independent regulator review.",cited_refs=pack.citations[:2],use_ai_assistance=False,idempotency_key="closure52-response",expected_case_version=case.case_version);case=svc.repo.case(case.examination_case_id)
        svc.approve_response(case.examination_case_id,draft.response_id,"auditor-user",approval_rationale="Independent human checker approves the evidence-bound regulator response after reviewing its citations.",expected_case_version=case.case_version);case=svc.repo.case(case.examination_case_id)
        svc.deliver_response(case.examination_case_id,draft.response_id,"auditor-user",channel="regulator_portal",subject="Regulatory inquiry response",external_reference="EX-52",supplemental_submission_reference=None,idempotency_key="closure52-delivery",expected_case_version=case.case_version);case=svc.repo.case(case.examination_case_id)
        with pytest.raises(ReviewConflictError,match="document requests"):svc.close_examination(case.examination_case_id,"auditor-user",closure_rationale="Cannot close while regulator evidence requests remain open.",expected_case_version=case.case_version)
        svc.satisfy_document_request(case.examination_case_id,"supporting-doc","acct-controller",satisfied_refs=[{"type":"control_evidence","id":"ce-52","sha256":"b"*64}],expected_case_version=case.case_version);case=svc.repo.case(case.examination_case_id)
        svc.record_finding(case.examination_case_id,"acct-controller",finding_code="CTRL-52",severity="high",material=True,description="Material regulator finding requires documented remediation before examination closure.",source_refs=pack.citations[:1]);case=svc.repo.case(case.examination_case_id)
        with pytest.raises(ReviewConflictError,match="material examination findings"):svc.close_examination(case.examination_case_id,"auditor-user",closure_rationale="Material finding remains unresolved and blocks closure.",expected_case_version=case.case_version)
        with pytest.raises(ReviewConflictError,match="Release 53"):svc.resolve_finding(case.examination_case_id,"CTRL-52","auditor-user",rationale="Material findings can no longer bypass the Release 53 corrective-action program.",expected_case_version=case.case_version)
        rem=RegulatoryRemediationService(db,"tenant-a");plan=rem.create_plan(case.examination_case_id,"acct-controller",finding_code="CTRL-52",root_cause="The control execution and its evidence binding were incomplete for the regulatory reporting workflow.",corrective_action_summary="Implement the corrected evidence-bound control and preserve deployment evidence.",preventive_action_summary="Add preventive validation and monitoring to stop recurrence.",control_redesign_proposal="Redesign the control with deterministic validation, immutable evidence checkpoints and maker-checker review.",financial_impact_analysis="Read-only impact analysis; no financial record is changed by the remediation workflow.",accounting_impact_analysis="Read-only impact analysis; any accounting change remains in the governed accounting workflow.",owner_user_id="acct-controller",due_at=datetime.now(UTC)+timedelta(days=30))
        rem.approve_plan(plan.plan_id,"auditor-user",approval_rationale="Independent human approver validates the corrective action plan and its segregation-of-duties controls.")
        rem.add_task(plan.plan_id,"acct-controller",task_key="CTRL52-CAPA",task_type="corrective",description="Implement and evidence the corrected regulatory reporting control.",owner_user_id="acct-controller",dependency_keys=[],due_at=datetime.now(UTC)+timedelta(days=10));rem.complete_task(plan.plan_id,"CTRL52-CAPA","acct-controller",evidence_refs=[{"type":"implementation","id":"ctrl52","sha256":"d"*64}])
        cp=rem.lock_checkpoint(plan.plan_id,"acct-controller",checkpoint_key="CTRL52-IMPL",checkpoint_type="implementation_evidence",evidence_refs=[{"type":"implementation","id":"ctrl52","sha256":"d"*64}]);rem.retest_control(plan.plan_id,"reg-supervisor",control_key="CTRL52",methodology="Replay representative regulatory-report samples under the redesigned control.",expected_result="Every sample is evidence-bound and maker-checker validated.",observed_result="All sampled records passed the redesigned control.",outcome="pass",evidence_refs=[{"type":"retest","id":"ctrl52-retest","sha256":"e"*64}]);follow=rem.draft_followup(plan.plan_id,"acct-controller",response_text="The material control finding has completed corrective action, preventive action, independent retesting, and evidence-bound verification for regulator follow-up.",cited_refs=[{"type":"checkpoint","id":cp.checkpoint_id,"sha256":cp.payload_sha256}]);rem.approve_followup(plan.plan_id,follow.followup_id,"auditor-user",approval_rationale="Independent human checker approves the remediation follow-up response after verifying cited evidence.");rem.certify_closure(plan.plan_id,"reg-supervisor",conclusion="effective",closure_rationale="Independent closure certifier confirms the material finding remediation is implemented, retested, evidence-bound and effective.");case=svc.repo.case(case.examination_case_id)
        svc.add_commitment(case.examination_case_id,"auditor-user",commitment_key="FOLLOWUP-52",description="Complete the documented remediation follow-up and preserve evidence for regulator inspection.",due_at=datetime.now(UTC)+timedelta(days=10),owner_user_id="acct-controller",evidence_refs=[]);case=svc.repo.case(case.examination_case_id)
        with pytest.raises(ReviewConflictError,match="remediation commitments"):svc.close_examination(case.examination_case_id,"auditor-user",closure_rationale="Open human remediation commitment prevents examination closure.",expected_case_version=case.case_version)
        svc.complete_commitment(case.examination_case_id,"FOLLOWUP-52","acct-controller",evidence_refs=[{"type":"remediation_evidence","id":"follow-52","sha256":"c"*64}],expected_case_version=case.case_version);case=svc.repo.case(case.examination_case_id)
        closed=svc.close_examination(case.examination_case_id,"auditor-user",closure_rationale="All regulator document requests, material findings, human remediation commitments, and approved response delivery are complete.",expected_case_version=case.case_version);assert closed.status=="closed"


def test_traceability_audit_export_response_version_chain_and_authority_are_immutable_provenance_only():
    f=factory()
    with f() as db:
        svc,case,_=examination_fixture(db,"trace52");pack=svc.build_evidence_pack(case.examination_case_id,"acct-controller",expected_case_version=case.case_version);case=svc.repo.case(case.examination_case_id)
        r1=svc.draft_response(case.examination_case_id,"acct-controller",response_text="First human-reviewed draft cites the certified filing and supervisory submission evidence without claiming regulatory authority.",cited_refs=pack.citations[:2],use_ai_assistance=False,idempotency_key="trace52-r1",expected_case_version=case.case_version);case=svc.repo.case(case.examination_case_id)
        r2=svc.draft_response(case.examination_case_id,"acct-controller",response_text="Second version improves the explanation while preserving immutable lineage to the prior response and cited evidence pack.",cited_refs=pack.citations[:2],use_ai_assistance=False,idempotency_key="trace52-r2",expected_case_version=case.case_version)
        assert r2.previous_response_sha256==r1.response_sha256
        trace=svc.traceability(case.examination_case_id,"auditor-user");export=svc.audit_export(case.examination_case_id,"auditor-user")
        assert trace["responses"][1]["previous_response_sha256"]==r1.response_sha256 and "Release 49 certified filing" in trace["provenance"] and trace["authority"]["ai_can_approve_examination_response"] is False
        assert len(export["manifest_sha256"])==64 and export["financial_accounting_mutation_authority"] is False and export["human_response_approval_required"] is True


def test_worker_service_migration_and_domain_have_no_response_approval_financial_accounting_or_fund_authority():
    root=Path(__file__).resolve().parents[2];worker=(root/'backend/app/workers/regulatory_examination.py').read_text();service=(root/'backend/app/services/regulatory_examination.py').read_text();migration=(root/'backend/alembic/versions/0047_regulatory_examination.py').read_text();domain=(root/'backend/app/domain/regulatory_examination.py').read_text()
    for forbidden in ['approve_response(', 'deliver_response(', '_post_journal(', 'authorize_packet(', 'collect_funds(', 'move_money(', 'lease_and_dispatch(']:assert forbidden not in worker
    for forbidden in ['_post_journal(', 'authorize_packet(', 'collect_funds(', 'move_money(']:assert forbidden not in service
    assert 'down_revision="0046_regulatory_supervisory_control"' in migration and 'FORCE ROW LEVEL SECURITY' in migration and 'guard_regulatory_examination_evidence_packs_immutable' in migration and 'guard_regulatory_examination_responses_finalized_immutable' in migration
    assert '"ai_can_approve_examination_response": False' in domain and '"worker_can_represent_human_regulatory_authority": False' in domain
