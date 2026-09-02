from __future__ import annotations
import hashlib, json
from collections import defaultdict


def version_hash(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()


def program_execution_readiness(payload: dict) -> dict:
    workstreams = payload.get("workstreams", [])
    dependencies = payload.get("dependencies", [])
    checkpoints = payload.get("checkpoints", [])
    entities = set(payload.get("required_entity_ids", []))
    validated = set(payload.get("validated_entity_ids", []))
    commitment_links = payload.get("regulatory_commitment_links", [])
    completed_workstreams = sum(1 for x in workstreams if x.get("status") == "completed")
    evidence_complete = sum(1 for x in checkpoints if x.get("evidence_complete") is True)
    blocked_dependencies = [x for x in dependencies if x.get("status") in {"blocked", "overdue"}]
    entity_coverage = 1.0 if not entities else len(entities & validated) / len(entities)
    workstream_ratio = 1.0 if not workstreams else completed_workstreams / len(workstreams)
    evidence_ratio = 1.0 if not checkpoints else evidence_complete / len(checkpoints)
    commitment_ratio = 1.0 if not commitment_links else sum(1 for x in commitment_links if x.get("mapped") is True) / len(commitment_links)
    score = round(max(0, min(100, (workstream_ratio*30 + evidence_ratio*25 + entity_coverage*25 + commitment_ratio*20)*100 - len(blocked_dependencies)*10)), 2)
    blockers=[]
    if blocked_dependencies: blockers.append("blocked_or_overdue_dependencies")
    if workstream_ratio < 1: blockers.append("incomplete_workstreams")
    if evidence_ratio < 1: blockers.append("incomplete_implementation_evidence")
    if entity_coverage < 1: blockers.append("cross_entity_validation_incomplete")
    if commitment_ratio < 1: blockers.append("regulatory_commitment_linkage_incomplete")
    return {"readiness_score":score,"ready_for_independent_assurance":score>=90 and not blockers,"blockers":blockers,"entity_validation_coverage":round(entity_coverage,4),"human_decision_required":True}


def resource_capacity_risk(payload: dict) -> dict:
    capacity=float(payload.get("available_capacity",0) or 0)
    demand=float(payload.get("planned_demand",0) or 0)
    critical=int(payload.get("critical_workstream_count",0) or 0)
    overdue=int(payload.get("overdue_milestone_count",0) or 0)
    utilization=0 if capacity<=0 and demand<=0 else 999 if capacity<=0 else demand/capacity
    score=min(100, round(max(0,(utilization-0.7)*100)+critical*8+overdue*10,2))
    level="critical" if score>=80 else "high" if score>=60 else "moderate" if score>=35 else "low"
    return {"resource_capacity_risk_score":score,"risk_level":level,"utilization_ratio":round(utilization,3),"executive_attention_required":score>=60}


def effectiveness_assurance(payload: dict) -> dict:
    tests=payload.get("independent_tests",[])
    passed=sum(1 for x in tests if x.get("result")=="pass")
    failed=[x for x in tests if x.get("result")=="fail"]
    required=set(payload.get("required_entity_ids",[])); tested=set(x.get("entity_id") for x in tests if x.get("entity_id"))
    coverage=1.0 if not required else len(required & tested)/len(required)
    test_ratio=1.0 if not tests else passed/len(tests)
    residual=float(payload.get("residual_systemic_risk_score",100))
    eligible=bool(tests) and not failed and coverage==1.0 and residual <= float(payload.get("maximum_certifiable_residual_risk",25))
    return {"independent_test_pass_ratio":round(test_ratio,4),"cross_entity_test_coverage":round(coverage,4),"failed_test_count":len(failed),"residual_systemic_risk_score":residual,"eligible_for_human_executive_certification":eligible,"automated_certification_allowed":False}


def dependency_concentration(payload: dict) -> dict:
    by_dep=defaultdict(set)
    for w in payload.get("workstreams",[]):
        for dep in w.get("dependency_ids",[]): by_dep[dep].add(w.get("workstream_id"))
    concentrated=[{"dependency_id":k,"dependent_workstream_count":len(v)} for k,v in by_dep.items() if len(v)>=2]
    return {"concentrated_dependencies":sorted(concentrated,key=lambda x:x["dependent_workstream_count"],reverse=True),"concentration_detected":bool(concentrated)}
