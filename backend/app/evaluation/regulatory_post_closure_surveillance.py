from app.services.regulatory_post_closure_surveillance import RegulatoryPostClosureSurveillanceService

def evaluate_recurrence_signal(case:dict)->dict:
    score=RegulatoryPostClosureSurveillanceService.composite_recurrence_score(recurrence_score=case.get("recurrence_score",0),sustainability_decay_score=case.get("sustainability_decay_score",0),control_regression_score=case.get("control_regression_score",0),cross_entity_count=len(case.get("cross_entity_keys",[])))
    return {"score":score,"reopen_candidate":score>=0.75,"decision_authority":"human_only"}

def evaluate_traceability(case:dict)->dict:
    required=["closed_issue","surveillance_signal","recurrence_evidence","human_reopening","renewed_remediation","revalidation"]
    missing=[k for k in required if not case.get(k)]
    return {"passed":not missing,"missing":missing}
