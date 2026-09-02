from __future__ import annotations

from hashlib import sha256
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.domain.ai_change_management import (
    classify_promotion_risk, compare_experiment_metrics, deterministic_cohort,
    sha256_json, validate_configuration_payload,
)
from app.models.tenancy import TenantModel
from app.models.evaluation import EvaluationRunModel
from app.models.ai_change_management import (
    AIConfigurationSnapshotModel, AIEnvironmentAssignmentModel, AIConfigurationPromotionModel,
    AIExperimentModel, AIExperimentAssignmentModel, AIExperimentObservationModel,
    AIConfigurationDriftEventModel, AIChangeEventModel,
)
from app.repositories.ai_change_management import AIChangeManagementRepository
from app.services.ai_change_management import AIChangeManagementService, ai_change_management_model_contract
from app.core.ai_config_runtime import resolve_agent_runtime_configuration

TABLES = [
    TenantModel.__table__, EvaluationRunModel.__table__, AIConfigurationSnapshotModel.__table__, AIEnvironmentAssignmentModel.__table__,
    AIConfigurationPromotionModel.__table__, AIExperimentModel.__table__, AIExperimentAssignmentModel.__table__,
    AIExperimentObservationModel.__table__, AIConfigurationDriftEventModel.__table__, AIChangeEventModel.__table__,
]


def session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    for table in TABLES:
        table.create(engine)
    db = Session(engine)
    db.add(TenantModel(tenant_id="tenant_demo", slug="demo", display_name="Demo", tenant_type="demo", status="active", data_region="local"))
    db.commit()
    return db


def service(db: Session) -> AIChangeManagementService:
    return AIChangeManagementService(AIChangeManagementRepository(db, "tenant_demo"))


def add_eval(db: Session, run_id: str, decision: str = "pass") -> None:
    now=datetime.now(timezone.utc)
    db.add(EvaluationRunModel(
        run_id=run_id, tenant_id="tenant_demo", dataset_version="golden_claims_v1",
        candidate_version=run_id, baseline_version="baseline-v1", decision=decision,
        config_sha256="a"*64, case_count=10, pass_rate=1.0 if decision=="pass" else 0.0,
        regression_reasons=[], trace_id=None, started_at=now, completed_at=now,
    ))
    db.flush()


def test_configuration_hash_is_canonical_and_secret_keys_are_rejected():
    assert sha256_json({"b": 2, "a": 1}) == sha256_json({"a": 1, "b": 2})
    validate_configuration_payload({"model": "m1", "retrieval": {"top_k": 5}})
    try:
        validate_configuration_payload({"provider": {"api_key": "do-not-store"}})
        raise AssertionError("secret-like key should be rejected")
    except ValueError as exc:
        assert "secret-like" in str(exc)


def test_deterministic_cohort_is_stable_and_privacy_safe():
    first = deterministic_cohort(tenant_id="tenant_demo", experiment_id="exp_1", subject_key="claim-secret-id", challenger_basis_points=2500)
    second = deterministic_cohort(tenant_id="tenant_demo", experiment_id="exp_1", subject_key="claim-secret-id", challenger_basis_points=2500)
    assert first == second
    assert 0 <= first.bucket < 10000
    assert first.variant in {"champion", "challenger"}


def test_production_changes_are_high_risk():
    assert classify_promotion_risk(environment="production", configuration_type="retrieval").value == "high"
    assert classify_promotion_risk(environment="staging", configuration_type="retrieval").value == "standard"
    assert classify_promotion_risk(environment="staging", configuration_type="prompt").value == "high"


def test_production_promotion_requires_eval_and_independent_approval():
    db = session(); svc = service(db)
    add_eval(db, "eval_pass_1")
    snap = svc.create_snapshot(actor="admin_a", config_key="agents.default", version="2.0.0", configuration_type="bundle", payload={"model": "model-v2"}, evaluation_run_id="eval_pass_1")
    try:
        svc.request_promotion(actor="admin_a", snapshot_id=snap.snapshot_id, target_environment="production", evaluation_run_id=None, evaluation_decision=None)
        raise AssertionError("missing evaluation must block")
    except ValueError as exc:
        assert "passing linked evaluation" in str(exc)
    prom = svc.request_promotion(actor="admin_a", snapshot_id=snap.snapshot_id, target_environment="production", evaluation_run_id="eval_pass_1", evaluation_decision="pass")
    assert prom.status == "pending_approval" and prom.risk == "high"
    try:
        svc.decide_promotion(actor="admin_a", promotion_id=prom.promotion_id, approve=True, reason="self approval")
        raise AssertionError("self approval must block")
    except ValueError as exc:
        assert "self-approve" in str(exc)
    approved = svc.decide_promotion(actor="admin_b", promotion_id=prom.promotion_id, approve=True, reason="evaluation and change review passed")
    assert approved.status == "activated"
    assignment, active = svc.resolve(environment="production", config_key="agents.default")
    assert active.snapshot_id == snap.snapshot_id and assignment.assignment_version == 1


def test_standard_staging_retrieval_promotion_auto_activates_after_policy_checks():
    db=session(); svc=service(db)
    snap=svc.create_snapshot(actor="admin_a",config_key="rag.hybrid-retrieval",version="1.1.0",configuration_type="retrieval",payload={"rrf_k":70})
    prom=svc.request_promotion(actor="admin_a",snapshot_id=snap.snapshot_id,target_environment="staging",evaluation_run_id="eval1",evaluation_decision="pass")
    assert prom.status == "activated"
    assert svc.resolve(environment="staging",config_key="rag.hybrid-retrieval")[1].version == "1.1.0"


def test_rollback_switches_pointer_and_increments_assignment_version():
    db=session(); svc=service(db)
    v1=svc.create_snapshot(actor="a",config_key="rag.hybrid-retrieval",version="1",configuration_type="retrieval",payload={"rrf_k":60})
    v2=svc.create_snapshot(actor="a",config_key="rag.hybrid-retrieval",version="2",configuration_type="retrieval",payload={"rrf_k":80})
    svc.request_promotion(actor="a",snapshot_id=v1.snapshot_id,target_environment="staging",evaluation_run_id="e1",evaluation_decision="pass")
    svc.request_promotion(actor="a",snapshot_id=v2.snapshot_id,target_environment="staging",evaluation_run_id="e2",evaluation_decision="pass")
    before=svc.resolve(environment="staging",config_key="rag.hybrid-retrieval")[0].assignment_version
    rolled=svc.rollback(actor="b",environment="staging",config_key="rag.hybrid-retrieval",target_snapshot_id=v1.snapshot_id,reason="latency regression")
    assert rolled.snapshot_id == v1.snapshot_id and rolled.assignment_version == before+1 and rolled.source == "rollback"


def test_production_ab_experiment_is_draft_until_independent_start_approval():
    db=session(); svc=service(db)
    add_eval(db,"eval_champion"); add_eval(db,"eval_challenger")
    c=svc.create_snapshot(actor="creator",config_key="agents.default",version="1",configuration_type="bundle",payload={"model":"m1"},evaluation_run_id="eval_champion")
    n=svc.create_snapshot(actor="creator",config_key="agents.default",version="2",configuration_type="bundle",payload={"model":"m2"},evaluation_run_id="eval_challenger")
    prom=svc.request_promotion(actor="creator",snapshot_id=c.snapshot_id,target_environment="production",evaluation_run_id="eval_champion",evaluation_decision="pass")
    svc.decide_promotion(actor="approver0",promotion_id=prom.promotion_id,approve=True,reason="establish champion")
    exp=svc.create_experiment(actor="creator",experiment_key="model-ab-1",environment="production",mode="ab",champion_snapshot_id=c.snapshot_id,challenger_snapshot_id=n.snapshot_id,challenger_basis_points=1000,evaluation_baseline_id="base1",guardrails={})
    assert exp.status == "draft"
    try:
        svc.start_experiment(actor="creator",experiment_id=exp.experiment_id,approval_reason="self")
        raise AssertionError("self approval must block")
    except ValueError: pass
    assert svc.start_experiment(actor="approver",experiment_id=exp.experiment_id,approval_reason="approved controlled exposure").status == "running"
    a1=svc.assign_experiment(experiment_id=exp.experiment_id,subject_key="claim-123")
    a2=svc.assign_experiment(experiment_id=exp.experiment_id,subject_key="claim-123")
    assert a1.assignment_id == a2.assignment_id
    assert a1.subject_sha256 == sha256(b"claim-123").hexdigest()
    assert "claim-123" not in a1.subject_sha256


def test_shadow_experiment_runs_without_user_visible_routing_contract():
    db=session(); svc=service(db)
    c=svc.create_snapshot(actor="a",config_key="agents.policy",version="1",configuration_type="prompt",payload={"prompt_version":"1"})
    n=svc.create_snapshot(actor="a",config_key="agents.policy",version="2",configuration_type="prompt",payload={"prompt_version":"2"})
    exp=svc.create_experiment(actor="a",experiment_key="shadow-policy",environment="production",mode="shadow",champion_snapshot_id=c.snapshot_id,challenger_snapshot_id=n.snapshot_id,challenger_basis_points=5000,evaluation_baseline_id="base",guardrails={})
    assert exp.status == "running" and exp.shadow_only is True


def test_quality_regression_blocks_even_when_challenger_is_cheaper_and_faster():
    result=compare_experiment_metrics(
        champion={"quality":.95,"latency_ms":1000,"cost_usd":.10},
        challenger={"quality":.88,"latency_ms":500,"cost_usd":.05},
        guardrails={"quality_floor":.90,"max_quality_regression":.01,"max_latency_regression_fraction":.2,"max_cost_regression_fraction":.25},
    )
    assert result["decision"] == "block"
    assert "challenger_quality_below_floor" in result["reasons"]


def test_experiment_observations_generate_cost_quality_latency_comparison():
    db=session(); svc=service(db)
    c=svc.create_snapshot(actor="a",config_key="rag.hybrid-retrieval",version="1",configuration_type="retrieval",payload={"rrf_k":60})
    n=svc.create_snapshot(actor="a",config_key="rag.hybrid-retrieval",version="2",configuration_type="retrieval",payload={"rrf_k":70})
    exp=svc.create_experiment(actor="a",experiment_key="rag-shadow",environment="staging",mode="shadow",champion_snapshot_id=c.snapshot_id,challenger_snapshot_id=n.snapshot_id,challenger_basis_points=5000,evaluation_baseline_id="base",guardrails={})
    evidence="a"*64
    svc.observe_experiment(experiment_id=exp.experiment_id,assignment_id=None,variant="champion",quality_score=.95,latency_ms=1000,cost_usd=.1,evaluation_run_id="e1",trace_id="t1",evidence_sha256=evidence)
    svc.observe_experiment(experiment_id=exp.experiment_id,assignment_id=None,variant="challenger",quality_score=.96,latency_ms=1050,cost_usd=.11,evaluation_run_id="e2",trace_id="t2",evidence_sha256=evidence)
    summary=svc.experiment_summary(exp.experiment_id)
    assert summary["decision"] == "pass" and summary["challenger"]["quality"] == .96


def test_drift_detection_compares_canonical_payload_hash():
    db=session(); svc=service(db)
    snap=svc.create_snapshot(actor="a",config_key="rag.hybrid-retrieval",version="1",configuration_type="retrieval",payload={"rrf_k":60})
    svc.request_promotion(actor="a",snapshot_id=snap.snapshot_id,target_environment="staging",evaluation_run_id="e1",evaluation_decision="pass")
    ok=svc.drift_check(actor="scanner",environment="staging",config_key="rag.hybrid-retrieval",observed_payload={"rrf_k":60})
    bad=svc.drift_check(actor="scanner",environment="staging",config_key="rag.hybrid-retrieval",observed_payload={"rrf_k":61})
    assert ok.status == "in_sync" and bad.status == "drift_detected"


def test_runtime_agent_bundle_resolves_active_snapshot():
    db=session(); svc=service(db)
    snap=svc.create_snapshot(actor="a",config_key="agents.default",version="3.2.0",configuration_type="bundle",payload={"model":"model-3","fallback_model":"fallback-3","prompt_version":"3.2.0","role_overrides":{"policy":"tenant-approved policy role"}})
    # Staging model/prompt bundle is high risk and needs independent approval.
    prom=svc.request_promotion(actor="a",snapshot_id=snap.snapshot_id,target_environment="staging",evaluation_run_id="e",evaluation_decision="pass")
    assert prom.status == "pending_approval"
    svc.decide_promotion(actor="b",promotion_id=prom.promotion_id,approve=True,reason="approved")
    runtime=resolve_agent_runtime_configuration(session=db,tenant_id="tenant_demo",environment="staging",config_key="agents.default",default_model="default",default_fallback_model="fb",default_prompt_version="1",enabled=True,required=True)
    assert runtime.snapshot_id == snap.snapshot_id
    assert runtime.model == "model-3" and runtime.prompt_version == "3.2.0"
    assert runtime.role_overrides["policy"] == "tenant-approved policy role"


def test_public_model_contract_documents_governance_boundaries():
    model=ai_change_management_model_contract()
    assert model["promotion"]["production_requires_passing_evaluation"] is True
    assert model["experiments"]["shadow_output_can_drive_claim_decision"] is False
    assert "immutable" in model["registry"]


def test_shadow_runtime_resolver_never_routes_challenger_to_effective_path():
    db=session(); svc=service(db)
    champion=svc.create_snapshot(actor="a",config_key="rag.shadow-test",version="1",configuration_type="retrieval",payload={"top_k":5})
    challenger=svc.create_snapshot(actor="a",config_key="rag.shadow-test",version="2",configuration_type="retrieval",payload={"top_k":7})
    svc.request_promotion(actor="a",snapshot_id=champion.snapshot_id,target_environment="staging",evaluation_run_id="e",evaluation_decision="pass")
    exp=svc.create_experiment(actor="a",experiment_key="shadow-runtime",environment="staging",mode="shadow",champion_snapshot_id=champion.snapshot_id,challenger_snapshot_id=challenger.snapshot_id,challenger_basis_points=5000,evaluation_baseline_id=None,guardrails={})
    resolved=svc.resolve_for_subject(environment="staging",config_key="rag.shadow-test",experiment_id=exp.experiment_id,subject_key="claim-777")
    assert resolved["effective_snapshot_id"] == champion.snapshot_id
    assert resolved["effective_variant"] == "champion"
    assert resolved["shadow_snapshot_id"] == challenger.snapshot_id


def test_caller_cannot_fabricate_passing_production_evaluation():
    db=session(); svc=service(db)
    add_eval(db,"eval_failed",decision="block")
    snap=svc.create_snapshot(actor="a",config_key="agents.default",version="4",configuration_type="bundle",payload={"model":"m4"},evaluation_run_id="eval_failed")
    try:
        svc.request_promotion(actor="a",snapshot_id=snap.snapshot_id,target_environment="production",evaluation_run_id="eval_failed",evaluation_decision="pass")
        raise AssertionError("authoritative failed evaluation must block")
    except ValueError as exc:
        assert "passing linked evaluation" in str(exc)


def test_rollback_cannot_activate_snapshot_never_approved_for_environment():
    db=session(); svc=service(db)
    approved=svc.create_snapshot(actor="a",config_key="rag.rollback-test",version="1",configuration_type="retrieval",payload={"k":1})
    unapproved=svc.create_snapshot(actor="a",config_key="rag.rollback-test",version="2",configuration_type="retrieval",payload={"k":2})
    svc.request_promotion(actor="a",snapshot_id=approved.snapshot_id,target_environment="staging",evaluation_run_id="e",evaluation_decision="pass")
    try:
        svc.rollback(actor="b",environment="staging",config_key="rag.rollback-test",target_snapshot_id=unapproved.snapshot_id,reason="try bypass")
        raise AssertionError("unapproved rollback target must block")
    except ValueError as exc:
        assert "never previously activated" in str(exc)
