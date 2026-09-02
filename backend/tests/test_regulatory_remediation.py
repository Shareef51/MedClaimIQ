from __future__ import annotations
from datetime import UTC,datetime,timedelta
from pathlib import Path
import pytest
from app.services.regulatory_remediation import RegulatoryRemediationService
from app.services.review_workbench import ReviewConflictError
from tests.test_regulatory_examination import examination_fixture


def finding_fixture(db,key="p53",*,ai=False):
    exam,case,_=examination_fixture(db,key)
    finding=exam.record_finding(case.examination_case_id,"acct-controller",finding_code=f"MAT-{key}",severity="high",material=True,description="Material regulatory control finding requires evidence-bound corrective and preventive action with independent retesting.",source_refs=[{"type":"regulatory_evidence","id":key,"sha256":"a"*64}])
    rem=RegulatoryRemediationService(db,"tenant-a")
    plan=rem.create_plan(case.examination_case_id,"acct-controller",finding_code=finding.finding_code,root_cause="Control execution evidence was not consistently bound to the certified reporting workflow.",corrective_action_summary="Implement evidence-bound control execution and exception escalation for every affected reporting cycle.",preventive_action_summary="Add preventive validation, training, and monitoring so the control cannot silently regress.",control_redesign_proposal="Redesign the control with deterministic validation, maker-checker review, immutable evidence checkpoints, and explicit fail-closed escalation.",financial_impact_analysis="Read-only impact analysis confirms no autonomous balance, payment, or fund movement changes are permitted by remediation automation.",accounting_impact_analysis="Read-only accounting impact analysis requires any accounting correction to remain in the separately governed human accounting workflow.",owner_user_id="acct-controller",due_at=datetime.now(UTC)+timedelta(days=30),use_ai_assistance=ai)
    return exam,rem,case,finding,plan

def complete_plan(rem,plan):
    rem.approve_plan(plan.plan_id,"auditor-user",approval_rationale="Independent human approver accepts the corrective-action plan after reviewing root cause, redesign, and read-only financial/accounting impact.")
    rem.add_task(plan.plan_id,"acct-controller",task_key="CAPA-1",task_type="corrective",description="Implement the corrected evidence-bound control and preserve exact deployment evidence.",owner_user_id="acct-controller",dependency_keys=[],due_at=datetime.now(UTC)+timedelta(days=10))
    rem.add_task(plan.plan_id,"acct-controller",task_key="CAPA-2",task_type="preventive",description="Deploy preventive monitoring and reviewer training after the corrective control is implemented.",owner_user_id="acct-controller",dependency_keys=["CAPA-1"],due_at=datetime.now(UTC)+timedelta(days=15))
    with pytest.raises(ReviewConflictError,match="dependencies"):rem.complete_task(plan.plan_id,"CAPA-2","acct-controller",evidence_refs=[{"type":"implementation","id":"premature"}])
    rem.complete_task(plan.plan_id,"CAPA-1","acct-controller",evidence_refs=[{"type":"deployment_evidence","id":"deploy-53","sha256":"b"*64}])
    rem.complete_task(plan.plan_id,"CAPA-2","acct-controller",evidence_refs=[{"type":"monitoring_evidence","id":"monitor-53","sha256":"c"*64}])
    cp=rem.lock_checkpoint(plan.plan_id,"acct-controller",checkpoint_key="implementation-v1",checkpoint_type="implementation_evidence",evidence_refs=[{"type":"control_evidence","id":"control-53","sha256":"d"*64}])
    rem.retest_control(plan.plan_id,"reg-supervisor",control_key="reporting-control",methodology="Independently replay the control over representative certified-report samples and compare deterministic expected outcomes.",expected_result="All sampled records pass the redesigned evidence and maker-checker control.",observed_result="All sampled records passed with immutable evidence and no unexplained exceptions.",outcome="pass",evidence_refs=[{"type":"retest_evidence","id":"retest-53","sha256":"e"*64}])
    follow=rem.draft_followup(plan.plan_id,"acct-controller",response_text="The corrective and preventive actions are implemented, independently retested, and supported by the cited immutable evidence for regulator follow-up review.",cited_refs=[{"type":"remediation_checkpoint","id":cp.checkpoint_id,"sha256":cp.payload_sha256}])
    rem.approve_followup(plan.plan_id,follow.followup_id,"auditor-user",approval_rationale="Independent human checker verifies the remediation evidence and approves the regulator follow-up response.")
    return cp

def test_material_finding_requires_governed_capa_and_independent_closure():
    from tests.test_recovery_control_assurance import factory
    f=factory()
    with f() as db:
        exam,rem,case,finding,plan=finding_fixture(db,"material53",ai=True)
        assert plan.ai_authority=="none" and plan.ai_recommendation["authority"]=="none" and plan.risk_level in {"high","critical"}
        with pytest.raises(ReviewConflictError,match="Release 53"):exam.resolve_finding(case.examination_case_id,finding.finding_code,"auditor-user",rationale="Direct resolution is forbidden for material findings.",expected_case_version=exam.repo.case(case.examination_case_id).case_version)
        with pytest.raises(ReviewConflictError,match="approver required"):rem.approve_plan(plan.plan_id,"acct-controller",approval_rationale="An accounting controller is not a remediation approver under segregation of duties.")
        complete_plan(rem,plan)
        cert=rem.certify_closure(plan.plan_id,"reg-supervisor",conclusion="effective",closure_rationale="Independent closure certifier confirms all CAPA tasks, implementation evidence, control retest, and regulator follow-up governance are complete and effective.")
        assert len(cert.certification_sha256)==64 and rem.exam.findings(case.examination_case_id)[-1].status=="resolved" and rem.repo.plan(plan.plan_id).status=="closed"

def test_waiver_governance_blocks_effective_closure_and_hash_chains_provenance():
    from tests.test_recovery_control_assurance import factory
    f=factory()
    with f() as db:
        _,rem,_,_,plan=finding_fixture(db,"waiver53")
        complete_plan(rem,plan)
        w=rem.request_waiver(plan.plan_id,"acct-controller",waiver_key="TEMP-53",waiver_type="temporary_exception",rationale="Temporary exception is requested while an external dependency is remediated.",risk_acceptance="Residual risk is documented and requires independent approval before any temporary exception can be recognized.",expires_at=datetime.now(UTC)+timedelta(days=5))
        rem.decide_waiver(plan.plan_id,w.waiver_key,"auditor-user",approve=True,decision_rationale="Independent human reviewer temporarily accepts the documented exception risk.")
        with pytest.raises(ReviewConflictError,match="waiver/exception"):rem.certify_closure(plan.plan_id,"reg-supervisor",conclusion="effective",closure_rationale="Closure must fail while a live approved waiver exists, regardless of passing control retest evidence.")
        trace=rem.traceability(plan.plan_id,"auditor-user");assert trace["audit_chain"] and all(len(x["event_sha256"])==64 for x in trace["audit_chain"])

def test_regulatory_remediation_frontend_migration_worker_and_authority_contracts():
    root=Path(__file__).resolve().parents[2]
    domain=(root/'backend/app/domain/regulatory_remediation.py').read_text();worker=(root/'backend/app/workers/regulatory_remediation.py').read_text();migration=(root/'backend/alembic/versions/0048_regulatory_remediation.py').read_text();sse=(root/'backend/app/api/v1/review_workbench.py').read_text()
    for token in ['"ai_can_approve_remediation": False','"worker_can_close_finding": False','independent_closure_certification_required']:assert token in domain
    for forbidden in ['approve_plan(', 'certify_closure(', 'retest_control(', '_post_journal(', 'authorize_packet(', 'collect_funds(', 'move_money(']:assert forbidden not in worker
    for token in ['FORCE ROW LEVEL SECURITY','guard_regulatory_remediation_checkpoints_immutable','guard_regulatory_remediation_followups_finalized_immutable','guard_regulatory_remediation_closure_certifications_immutable']:assert token in migration
    assert 'regulatory_remediation.' in sse
