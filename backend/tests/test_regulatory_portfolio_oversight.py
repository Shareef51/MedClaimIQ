from __future__ import annotations
from datetime import UTC,datetime,timedelta
from pathlib import Path
import pytest
from app.services.regulatory_portfolio_oversight import RegulatoryPortfolioOversightService
from app.services.review_workbench import ReviewConflictError
from tests.test_regulatory_remediation import finding_fixture
from tests.test_recovery_control_assurance import factory


def portfolio_fixture(db,key="p54"):
    exam,rem,case,_,p1=finding_fixture(db,key+"a")
    finding2=exam.record_finding(case.examination_case_id,"acct-controller",finding_code=f"MAT-{key}b",severity="high",material=True,description="Repeated material regulatory control finding shows the same evidence-binding weakness across another control occurrence.",source_refs=[{"type":"regulatory_evidence","id":key+"b","sha256":"f"*64}])
    p2=rem.create_plan(case.examination_case_id,"acct-controller",finding_code=finding2.finding_code,root_cause="Control execution evidence was not consistently bound to the certified reporting workflow.",corrective_action_summary="Implement evidence-bound control execution and exception escalation for every affected reporting cycle.",preventive_action_summary="Add preventive validation, training, and monitoring so the control cannot silently regress.",control_redesign_proposal="Redesign the control with deterministic validation, maker-checker review, immutable evidence checkpoints, and explicit fail-closed escalation.",financial_impact_analysis="Read-only impact analysis confirms no autonomous balance, payment, or fund movement changes are permitted by remediation automation.",accounting_impact_analysis="Read-only accounting impact analysis requires any accounting correction to remain in the separately governed human accounting workflow.",owner_user_id="acct-controller",due_at=datetime.now(UTC)+timedelta(days=30),use_ai_assistance=False)
    svc=RegulatoryPortfolioOversightService(db,"tenant-a")
    ctl=svc.register_control("acct-controller",control_key=f"CTRL-{key}",name="Regulatory reporting evidence binding",description="Enterprise control requiring immutable evidence and maker-checker validation across regulatory remediation programs.",control_family="regulatory_reporting",owner_user_id="acct-controller")
    svc.map_control(ctl.control_id,"acct-controller",plan_id=p1.plan_id,mapping_rationale="The remediation corrects the enterprise reporting evidence-binding control.")
    svc.map_control(ctl.control_id,"acct-controller",plan_id=p2.plan_id,mapping_rationale="The repeated finding maps to the same enterprise reporting evidence-binding control.")
    snap=svc.prepare_snapshot("acct-controller",period_key=f"{key}-2026-Q3")
    return svc,snap,ctl,p1,p2


def test_cross_examination_aggregation_recurring_root_causes_repeat_findings_and_control_clusters_are_read_only():
    f=factory()
    with f() as db:
        svc,snap,ctl,p1,p2=portfolio_fixture(db,"aggregate54");before=[(p.plan_id,p.plan_sha256,p.status) for p in (p1,p2)]
        view=svc.snapshot_view(snap.snapshot_id,"auditor-user")
        assert view["metrics"]["plan_count"]>=2 and view["metrics"]["recurring_root_cause_count"]>=1 and view["metrics"]["systemic_cluster_count"]>=2
        assert any(c["type"]=="systemic_control" and ctl.control_id in c["cluster_key"] for c in view["clusters"])
        assert all(c["recommendation"]["authority"]=="none" for c in view["clusters"])
        assert [(p.plan_id,p.plan_sha256,p.status) for p in (p1,p2)]==before


def test_independent_control_campaign_management_attestation_and_separate_portfolio_certification():
    f=factory()
    with f() as db:
        svc,snap,ctl,_,_=portfolio_fixture(db,"cert54")
        camp=svc.create_testing_campaign(snap.snapshot_id,"acct-controller",campaign_key="Q3-independent",methodology="Independently sample both mapped findings, replay the enterprise control, and verify immutable remediation evidence and non-recurrence.",control_ids=[ctl.control_id],due_at=datetime.now(UTC)+timedelta(days=14))
        with pytest.raises(ReviewConflictError,match="different humans"):svc.record_test_result(camp.campaign_id,"acct-controller",control_id=ctl.control_id,outcome="pass",observations="Self-testing must not be accepted.",evidence_refs=[{"type":"test","id":"self"}])
        result=svc.record_test_result(camp.campaign_id,"auditor-user",control_id=ctl.control_id,outcome="pass",observations="Independent testing found the enterprise control operating effectively across the sampled remediated findings.",evidence_refs=[{"type":"independent_test","id":"test-54","sha256":"a"*64}]);assert len(result.payload_sha256)==64
        with pytest.raises(ReviewConflictError,match="management attester"):svc.management_attest(snap.snapshot_id,"acct-controller",conclusion="effective",rationale="The snapshot preparer cannot provide management attestation for the same portfolio snapshot.")
        att=svc.management_attest(snap.snapshot_id,"reg-supervisor",conclusion="effective",rationale="Management independently reviewed recurrence, portfolio risk, CAPA critical paths, enterprise control mapping, and independent control test evidence.")
        with pytest.raises(ReviewConflictError,match="different humans"):svc.certify_portfolio(snap.snapshot_id,"reg-supervisor",conclusion="effective",rationale="The management attester cannot also provide independent portfolio certification.")
        cert=svc.certify_portfolio(snap.snapshot_id,"auditor-user",conclusion="effective",rationale="Independent human certifier verifies the immutable portfolio snapshot, completed control testing, management attestation and systemic-risk governance.")
        assert att.attested_by_user_id=="reg-supervisor" and cert.certified_by_user_id=="auditor-user" and len(cert.certification_sha256)==64 and svc.repo.snapshot(snap.snapshot_id).status=="certified"


def test_risk_acceptance_is_maker_checker_and_board_package_preserves_immutable_source_provenance():
    f=factory()
    with f() as db:
        svc,snap,_,_,_=portfolio_fixture(db,"risk54")
        key=svc.repo.clusters(snap.snapshot_id)[0].cluster_key
        a=svc.request_risk_acceptance(snap.snapshot_id,"reg-supervisor",risk_key=key,rationale="Temporary portfolio risk acceptance is requested while the systemic control remediation is expanded enterprise-wide.",expires_at=datetime.now(UTC)+timedelta(days=30))
        with pytest.raises(ReviewConflictError,match="different humans"):svc.decide_risk_acceptance(snap.snapshot_id,key,"reg-supervisor",approve=True,decision_rationale="Requester cannot approve their own risk acceptance.")
        svc.decide_risk_acceptance(snap.snapshot_id,key,"auditor-user",approve=True,decision_rationale="Independent human reviewer accepts the time-bounded residual risk with continued monitoring and testing.")
        pkg=svc.board_regulatory_package(snap.snapshot_id,"auditor-user")
        assert a.requested_by_user_id=="reg-supervisor" and len(pkg["manifest_sha256"])==64 and pkg["manifest"]["financial_accounting_mutation_authority"] is False and pkg["manifest"]["ai_authority"]=="analysis_recommendation_only"


def test_release54_worker_migration_domain_and_sse_have_no_approval_financial_or_regulatory_authority():
    root=Path(__file__).resolve().parents[2];worker=(root/'backend/app/workers/regulatory_portfolio_oversight.py').read_text();domain=(root/'backend/app/domain/regulatory_portfolio_oversight.py').read_text();migration=(root/'backend/alembic/versions/0049_regulatory_portfolio_oversight.py').read_text();sse=(root/'backend/app/api/v1/review_workbench.py').read_text()
    for token in ['"ai_can_certify_controls": False','"worker_can_certify_portfolio": False','"financial_accounting_mutation_authority": False','"fund_movement": False']:assert token in domain
    for forbidden in ['certify_portfolio(', 'management_attest(', 'record_test_result(', 'decide_risk_acceptance(', '_post_journal(', 'authorize_packet(', 'collect_funds(', 'move_money(']:assert forbidden not in worker
    assert 'down_revision="0048_regulatory_remediation"' in migration and 'FORCE ROW LEVEL SECURITY' in migration and 'guard_regulatory_portfolio_snapshots_immutable' in migration and 'guard_regulatory_portfolio_certifications_immutable' in migration
    assert 'regulatory_portfolio.' in sse
