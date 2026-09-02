import pytest
from app.domain.production_performance_resilience_disaster_recovery_operational_readiness import *
from app.evaluation.production_performance_resilience_disaster_recovery_operational_readiness import *
from app.services.production_performance_resilience_disaster_recovery_operational_readiness import ProductionPerformanceResilienceDisasterRecoveryOperationalReadinessService

def _good_profiles():
    return [{"profile":p,"target_rps":100,"observed_rps":110,"p95_ms":500,"p95_budget_ms":1000,"p99_ms":900,"p99_budget_ms":2000,"error_rate":0.001,"error_rate_budget":0.01,"data_integrity_preserved":True,"duration_minutes":120 if p=="soak" else 10} for p in REQUIRED_LOAD_PROFILES]

def _good_operational_payload():
    return {"release_id":"rel-109","candidate_version":"v109","release107_release_candidate_decision_version_id":"rc-107","release108_release_security_certification_version_id":"sec-108","gates":{x:True for x in REQUIRED_OPERATIONAL_GATES},"open_operational_risks":[],"evidence_refs":["load.json","dr.json","alerts.json"]}

def test_performance_noisy_neighbor_and_ai_slo_gates():
    assert assess_load_stress_soak({"profiles":_good_profiles(),"minimum_soak_minutes":60})["load_stress_soak_passed"] is True
    noisy={"cases":[{"case_id":"n1","tenant_isolation_preserved":True,"rate_limit_or_quota_enforced":True,"resource_fairness_preserved":True,"victim_p95_degradation_fraction":0.10,"degradation_budget_fraction":0.25}]}
    assert assess_noisy_neighbor(noisy)["tenant_noisy_neighbor_passed"] is True
    comps=[{"component":c,"p95_ms":100,"p95_budget_ms":500,"error_rate":0.001,"error_rate_budget":0.02,"cost_per_case_usd":0.01,"cost_budget_per_case_usd":0.10,"quality_gate_passed":True} for c in REQUIRED_AI_SLO_COMPONENTS]
    assert assess_ai_rag_agent_slo_cost({"components":comps})["ai_rag_agent_slo_cost_passed"] is True

def test_dependency_provider_kubernetes_and_dr_are_fail_closed():
    deps=[{"dependency":d,"recovered":True,"data_integrity_preserved":True,"tenant_isolation_preserved":True,"backpressure_or_circuit_breaker_worked":True,"data_loss":False,"data_corruption":False} for d in REQUIRED_DEPENDENCY_DRILLS]
    assert assess_dependency_resilience({"drills":deps})["dependency_resilience_passed"] is True
    deps[0]["data_loss"]=True
    assert assess_dependency_resilience({"drills":deps})["dependency_resilience_passed"] is False
    provider={"cases":[{"case_id":"p1","timeout_bounded":True,"circuit_breaker_opened":True,"no_silent_model_substitution":True,"quality_risk_policy_preserved":True,"tenant_policy_preserved":True,"human_escalation_when_required":True,"fallback_used":True,"fallback_authorized":True}]}
    assert assess_provider_outage_fallback(provider)["provider_outage_fallback_passed"] is True
    kube=[{"failure_mode":x,"service_recovered":True,"workload_rescheduled":True,"data_integrity_preserved":True,"recovery_seconds":30,"recovery_budget_seconds":300} for x in REQUIRED_KUBERNETES_DRILLS]
    assert assess_kubernetes_disruption({"drills":kube})["kubernetes_disruption_passed"] is True
    stores=[{"store":x,"backup_verified":True,"restore_completed":True,"checksum_verified":True,"point_in_time_recovery_tested":True,"data_loss":False} for x in ["postgresql","object_storage","vector_store"]]
    assert assess_backup_restore({"stores":stores})["backup_restore_passed"] is True
    services=[{"service":"api","observed_rpo_seconds":30,"rpo_target_seconds":60,"observed_rto_seconds":120,"rto_target_seconds":300,"data_integrity_verified":True}]
    assert assess_dr_rpo_rto({"services":services})["dr_rpo_rto_passed"] is True

def test_capacity_observability_incident_and_readiness_require_full_evidence():
    capacity={"forecast_horizon_days":90,"services":[{"service":"api","scale_out_triggered":True,"scale_in_stable":True,"headroom_fraction":0.40,"minimum_headroom_fraction":0.30,"saturation_fraction":0.60,"maximum_saturation_fraction":0.80}]}
    assert assess_autoscaling_capacity(capacity)["autoscaling_capacity_passed"] is True
    surfaces=[{"surface":x,"metrics_present":True,"logs_present":True,"traces_present":True,"alert_fired":True,"runbook_linked":True,"oncall_route_verified":True} for x in REQUIRED_OBSERVABILITY_SURFACES]
    assert assess_observability_alert_runbooks({"surfaces":surfaces})["observability_alert_runbooks_passed"] is True
    exercises=[{"exercise_id":"sev1-game-day","incident_commander_assigned":True,"severity_declared":True,"communications_exercised":True,"rollback_or_mitigation_exercised":True,"evidence_preserved":True,"postmortem_actions_recorded":True}]
    assert assess_incident_response_exercise({"exercises":exercises})["incident_response_exercise_passed"] is True
    p=_good_operational_payload(); assert operational_go_live_readiness(p)["operational_go_live_ready"] is True
    p["open_operational_risks"]=[{"risk_id":"R1","severity":"sev1","category":"data_loss","status":"open"}]
    r=operational_go_live_readiness(p); assert r["operational_go_live_ready"] is False and "R1" in r["non_bypassable_operational_risks"]

def test_operational_drill_and_certification_are_human_only_and_provenance_bound():
    assert OPERATIONAL_READINESS_AUTHORITY["ai_can_issue_operational_certification"] is False
    svc=ProductionPerformanceResilienceDisasterRecoveryOperationalReadinessService(None,"tenant-a")
    p=_good_operational_payload()|{"actor_role":"site_reliability_engineer","environment":"preproduction","suite_name":"release109"}
    run=svc.create_drill_run("sre-1",p); assert run["human_initiated"] is True and run["immutable"] is True
    bad=dict(p); bad["release108_release_security_certification_version_id"]=None
    with pytest.raises(ValueError): svc.create_drill_run("sre-1",bad)
    with pytest.raises(PermissionError): svc.certify("agent",{"actor_role":"ai_agent"})
    ready=operational_go_live_readiness(_good_operational_payload())
    cert=svc.certify("cto-1",{"actor_role":"chief_technology_officer","release_id":"rel-109","candidate_version":"v109","release107_release_candidate_decision_version_id":"rc-107","release108_release_security_certification_version_id":"sec-108","operational_drill_run_version_id":run["operational_drill_run_version_id"],"readiness":ready,"decision":"certify","rationale":"all operational gates pass","evidence_refs":["ops-pack.json"]})
    assert cert["human_decision"] is True and cert["automated_production_promotion"] is False and cert["immutable"] is True
