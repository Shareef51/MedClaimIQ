from __future__ import annotations
import hashlib, json


def version_hash(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()


def root_cause_comparison(prior: dict, current: dict) -> dict:
    prior_ids=set(prior.get("root_cause_ids",[])); current_ids=set(current.get("root_cause_ids",[]))
    shared=sorted(prior_ids & current_ids)
    prior_controls=set(prior.get("control_ids",[])); current_controls=set(current.get("control_ids",[]))
    shared_controls=sorted(prior_controls & current_controls)
    same_primary=bool(prior.get("primary_root_cause_id")) and prior.get("primary_root_cause_id")==current.get("primary_root_cause_id")
    return {"same_primary_root_cause":same_primary,"shared_root_cause_ids":shared,"shared_control_ids":shared_controls,"systemic_recurrence_supported":same_primary or bool(shared),"human_validation_required":True}


def propagation_readiness(payload: dict) -> dict:
    required=set(payload.get("required_entity_ids",[])); complete=set(payload.get("completed_entity_ids",[]))
    missing=sorted(required-complete)
    return {"required_entity_count":len(required),"completed_entity_count":len(required & complete),"missing_entity_ids":missing,"cross_entity_propagation_complete":not missing}


def second_systemic_recurrence(history: list[dict]) -> dict:
    confirmed=[x for x in history if x.get("confirmed",True) and x.get("event_type") in {"systemic_recurrence","program_reopen","control_regression"}]
    second=len(confirmed)>=2
    return {"confirmed_systemic_recurrence_count":len(confirmed),"second_systemic_recurrence":second,"executive_escalation_required":second,"internal_audit_escalation_required":second,"automatic_reclosure_allowed":False}


def reclosure_readiness(payload: dict) -> dict:
    gates={
        "renewed_plan_human_approved":bool(payload.get("renewed_plan_human_approved")),
        "all_milestones_complete":bool(payload.get("all_milestones_complete")),
        "cross_entity_remediation_complete":bool(payload.get("cross_entity_remediation_complete")),
        "regulator_commitments_reconciled":bool(payload.get("regulator_commitments_reconciled")),
        "evidence_complete":bool(payload.get("evidence_complete")),
        "independent_revalidation_passed":bool(payload.get("independent_revalidation_passed")),
        "sustainability_reset_complete":bool(payload.get("sustainability_reset_complete")),
        "human_residual_risk_reassessed":bool(payload.get("human_residual_risk_reassessed")),
        "second_systemic_recurrence_absent":not bool(payload.get("second_systemic_recurrence_detected")),
    }
    weights={"renewed_plan_human_approved":10,"all_milestones_complete":15,"cross_entity_remediation_complete":10,"regulator_commitments_reconciled":10,"evidence_complete":10,"independent_revalidation_passed":20,"sustainability_reset_complete":10,"human_residual_risk_reassessed":10,"second_systemic_recurrence_absent":5}
    score=sum(weights[k] for k,v in gates.items() if v); blockers=[k for k,v in gates.items() if not v]
    return {"reclosure_readiness_score":score,"ready_for_human_executive_recertification":score==100,"gates":gates,"blockers":blockers,"automated_reclosure_allowed":False}
