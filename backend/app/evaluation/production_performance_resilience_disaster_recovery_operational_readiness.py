from __future__ import annotations
import hashlib, json
from typing import Any
from app.domain.production_performance_resilience_disaster_recovery_operational_readiness import (
    REQUIRED_AI_SLO_COMPONENTS, REQUIRED_DEPENDENCY_DRILLS, REQUIRED_KUBERNETES_DRILLS,
    REQUIRED_LOAD_PROFILES, REQUIRED_OBSERVABILITY_SURFACES, REQUIRED_OPERATIONAL_GATES,
    NON_BYPASSABLE_CATEGORIES,
)

def version_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()

def _ok(value: Any) -> bool:
    if isinstance(value, bool): return value
    return str(value or "").lower() in {"pass","passed","ok","healthy","success","succeeded","validated","complete","recovered","within_budget","safe_fallback"}

def assess_load_stress_soak(payload: dict[str, Any]) -> dict[str, Any]:
    profiles=payload.get("profiles",[]); by={str(x.get("profile")):x for x in profiles}; missing=[x for x in REQUIRED_LOAD_PROFILES if x not in by]
    failed=[]
    for name in REQUIRED_LOAD_PROFILES:
        p=by.get(name)
        if not p: continue
        target_rps=float(p.get("target_rps",0)); observed=float(p.get("observed_rps",0)); p95=float(p.get("p95_ms",10**9)); p99=float(p.get("p99_ms",10**9)); err=float(p.get("error_rate",1))
        if observed < target_rps or p95 > float(p.get("p95_budget_ms",1500)) or p99 > float(p.get("p99_budget_ms",3000)) or err > float(p.get("error_rate_budget",0.01)) or not bool(p.get("data_integrity_preserved",False)):
            failed.append(name)
    soak=by.get("soak",{}); soak_duration_ok=float(soak.get("duration_minutes",0)) >= float(payload.get("minimum_soak_minutes",60))
    return {"missing_profiles":missing,"failed_profiles":failed,"soak_duration_ok":soak_duration_ok,"load_stress_soak_passed":not missing and not failed and soak_duration_ok}

def assess_noisy_neighbor(payload: dict[str, Any]) -> dict[str, Any]:
    cases=payload.get("cases",[]); failures=[]
    for c in cases:
        if not (bool(c.get("tenant_isolation_preserved")) and bool(c.get("rate_limit_or_quota_enforced")) and bool(c.get("resource_fairness_preserved")) and float(c.get("victim_p95_degradation_fraction",1)) <= float(c.get("degradation_budget_fraction",0.25))): failures.append(c.get("case_id","unnamed"))
    return {"failed_cases":failures,"tenant_isolation_breach":any(bool(c.get("tenant_isolation_preserved")) is False for c in cases),"tenant_noisy_neighbor_passed":bool(cases) and not failures}

def assess_ai_rag_agent_slo_cost(payload: dict[str, Any]) -> dict[str, Any]:
    comps=payload.get("components",[]); by={str(x.get("component")):x for x in comps}; missing=[x for x in REQUIRED_AI_SLO_COMPONENTS if x not in by]; failed=[]
    for name in REQUIRED_AI_SLO_COMPONENTS:
        c=by.get(name)
        if not c: continue
        if float(c.get("p95_ms",10**9)) > float(c.get("p95_budget_ms",10**9-1)) or float(c.get("error_rate",1)) > float(c.get("error_rate_budget",0.02)) or float(c.get("cost_per_case_usd",10**9)) > float(c.get("cost_budget_per_case_usd",10**9-1)) or not bool(c.get("quality_gate_passed",False)):
            failed.append(name)
    return {"missing_components":missing,"failed_components":failed,"ai_rag_agent_slo_cost_passed":not missing and not failed}

def assess_dependency_resilience(payload: dict[str, Any]) -> dict[str, Any]:
    drills=payload.get("drills",[]); by={str(x.get("dependency")):x for x in drills}; missing=[x for x in REQUIRED_DEPENDENCY_DRILLS if x not in by]; failed=[]; data_loss=[]
    for name in REQUIRED_DEPENDENCY_DRILLS:
        d=by.get(name)
        if not d: continue
        safe=bool(d.get("recovered")) and bool(d.get("data_integrity_preserved")) and bool(d.get("tenant_isolation_preserved")) and bool(d.get("backpressure_or_circuit_breaker_worked"))
        if not safe: failed.append(name)
        if bool(d.get("data_loss")) or bool(d.get("data_corruption")): data_loss.append(name)
    return {"missing_dependencies":missing,"failed_dependencies":failed,"data_loss_or_corruption":data_loss,"dependency_resilience_passed":not missing and not failed and not data_loss}

def assess_provider_outage_fallback(payload: dict[str, Any]) -> dict[str, Any]:
    cases=payload.get("cases",[]); failures=[]; unsafe=[]
    for c in cases:
        safe=bool(c.get("timeout_bounded")) and bool(c.get("circuit_breaker_opened")) and bool(c.get("no_silent_model_substitution")) and bool(c.get("quality_risk_policy_preserved")) and bool(c.get("tenant_policy_preserved")) and bool(c.get("human_escalation_when_required"))
        if c.get("fallback_used") and not bool(c.get("fallback_authorized")): safe=False; unsafe.append(c.get("case_id","unnamed"))
        if not safe: failures.append(c.get("case_id","unnamed"))
    return {"failed_cases":failures,"unsafe_fallback_cases":unsafe,"provider_outage_fallback_passed":bool(cases) and not failures}

def assess_kubernetes_disruption(payload: dict[str, Any]) -> dict[str, Any]:
    drills=payload.get("drills",[]); by={str(x.get("failure_mode")):x for x in drills}; missing=[x for x in REQUIRED_KUBERNETES_DRILLS if x not in by]; failed=[]
    for name in REQUIRED_KUBERNETES_DRILLS:
        d=by.get(name)
        if not d: continue
        if not (bool(d.get("service_recovered")) and bool(d.get("workload_rescheduled")) and bool(d.get("data_integrity_preserved")) and float(d.get("recovery_seconds",10**9)) <= float(d.get("recovery_budget_seconds",600))): failed.append(name)
    return {"missing_failure_modes":missing,"failed_failure_modes":failed,"kubernetes_disruption_passed":not missing and not failed}

def assess_backup_restore(payload: dict[str, Any]) -> dict[str, Any]:
    stores=payload.get("stores",[]); failed=[]
    for s in stores:
        if not (bool(s.get("backup_verified")) and bool(s.get("restore_completed")) and bool(s.get("checksum_verified")) and bool(s.get("point_in_time_recovery_tested",True)) and not bool(s.get("data_loss"))): failed.append(s.get("store","unnamed"))
    return {"failed_stores":failed,"backup_restore_passed":bool(stores) and not failed}

def assess_dr_rpo_rto(payload: dict[str, Any]) -> dict[str, Any]:
    services=payload.get("services",[]); rpo=[]; rto=[]; failed=[]
    for s in services:
        if float(s.get("observed_rpo_seconds",10**9)) > float(s.get("rpo_target_seconds",0)): rpo.append(s.get("service","unnamed"))
        if float(s.get("observed_rto_seconds",10**9)) > float(s.get("rto_target_seconds",0)): rto.append(s.get("service","unnamed"))
        if not bool(s.get("data_integrity_verified",False)): failed.append(s.get("service","unnamed"))
    return {"rpo_breaches":rpo,"rto_breaches":rto,"integrity_failures":failed,"dr_rpo_rto_passed":bool(services) and not rpo and not rto and not failed}

def assess_failover_failback(payload: dict[str, Any]) -> dict[str, Any]:
    drills=payload.get("drills",[]); failed=[]
    for d in drills:
        if not (bool(d.get("failover_completed")) and bool(d.get("traffic_validated")) and bool(d.get("writes_consistent")) and bool(d.get("failback_completed")) and bool(d.get("post_failback_integrity_verified"))): failed.append(d.get("drill_id","unnamed"))
    return {"failed_drills":failed,"failover_failback_passed":bool(drills) and not failed}

def assess_autoscaling_capacity(payload: dict[str, Any]) -> dict[str, Any]:
    services=payload.get("services",[]); failed=[]
    for s in services:
        if not (bool(s.get("scale_out_triggered")) and bool(s.get("scale_in_stable")) and float(s.get("headroom_fraction",0)) >= float(s.get("minimum_headroom_fraction",0.30)) and float(s.get("saturation_fraction",1)) <= float(s.get("maximum_saturation_fraction",0.80))): failed.append(s.get("service","unnamed"))
    return {"failed_services":failed,"capacity_forecast_horizon_days":int(payload.get("forecast_horizon_days",0)),"autoscaling_capacity_passed":bool(services) and not failed and int(payload.get("forecast_horizon_days",0))>=30}

def assess_observability_alert_runbooks(payload: dict[str, Any]) -> dict[str, Any]:
    surfaces=payload.get("surfaces",[]); by={str(x.get("surface")):x for x in surfaces}; missing=[x for x in REQUIRED_OBSERVABILITY_SURFACES if x not in by]; failed=[]
    for name in REQUIRED_OBSERVABILITY_SURFACES:
        s=by.get(name)
        if not s: continue
        if not (bool(s.get("metrics_present")) and bool(s.get("logs_present")) and bool(s.get("traces_present")) and bool(s.get("alert_fired")) and bool(s.get("runbook_linked")) and bool(s.get("oncall_route_verified"))): failed.append(name)
    return {"missing_surfaces":missing,"failed_surfaces":failed,"observability_alert_runbooks_passed":not missing and not failed}

def assess_incident_response_exercise(payload: dict[str, Any]) -> dict[str, Any]:
    exercises=payload.get("exercises",[]); failed=[]
    for e in exercises:
        if not (bool(e.get("incident_commander_assigned")) and bool(e.get("severity_declared")) and bool(e.get("communications_exercised")) and bool(e.get("rollback_or_mitigation_exercised")) and bool(e.get("evidence_preserved")) and bool(e.get("postmortem_actions_recorded"))): failed.append(e.get("exercise_id","unnamed"))
    return {"failed_exercises":failed,"incident_response_exercise_passed":bool(exercises) and not failed}

def operational_go_live_readiness(payload: dict[str, Any]) -> dict[str, Any]:
    gates=payload.get("gates",{}); blockers=[]
    for gate in REQUIRED_OPERATIONAL_GATES:
        if not _ok(gates.get(gate)): blockers.append(gate)
    risks=payload.get("open_operational_risks",[]); nonbypass=[]; unresolved=[]
    for r in risks:
        if str(r.get("status","open")).lower() in {"closed","resolved","mitigated"}: continue
        rid=r.get("risk_id","unnamed"); unresolved.append(rid)
        if r.get("category") in NON_BYPASSABLE_CATEGORIES or str(r.get("severity","")).lower()=="sev1": nonbypass.append(rid)
    provenance_ok=bool(payload.get("release107_release_candidate_decision_version_id")) and bool(payload.get("release108_release_security_certification_version_id"))
    if not provenance_ok: blockers.append("release_security_provenance")
    if not payload.get("evidence_refs"): blockers.append("evidence_pack")
    ready=not blockers and not nonbypass and not unresolved
    return {"gate_count":len(REQUIRED_OPERATIONAL_GATES),"blocking_gates":sorted(set(blockers)),"unresolved_operational_risks":unresolved,"non_bypassable_operational_risks":nonbypass,"provenance_complete":provenance_ok,"operational_go_live_ready":ready,"automated_certification":False,"automated_production_promotion":False}

def operational_evidence_pack(payload: dict[str, Any]) -> dict[str, Any]:
    readiness=operational_go_live_readiness(payload)
    pack={"release_id":payload.get("release_id"),"candidate_version":payload.get("candidate_version"),"release107_release_candidate_decision_version_id":payload.get("release107_release_candidate_decision_version_id"),"release108_release_security_certification_version_id":payload.get("release108_release_security_certification_version_id"),"readiness":readiness,"evidence_refs":sorted(set(payload.get("evidence_refs",[]))),"runbook_refs":sorted(set(payload.get("runbook_refs",[]))),"dashboard_refs":sorted(set(payload.get("dashboard_refs",[]))),"drill_refs":sorted(set(payload.get("drill_refs",[])))}
    return {**pack,"evidence_pack_hash":version_hash(pack),"immutable":True}
