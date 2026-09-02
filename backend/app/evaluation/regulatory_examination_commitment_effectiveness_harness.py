from app.domain.regulatory_examination_commitment_effectiveness import COMMITMENT_EFFECTIVENESS_AUTHORITY
from app.evaluation.regulatory_examination_commitment_effectiveness import closure_readiness,sustainability_state,recurrence_match

def evaluate_release69()->dict:
    authority=not COMMITMENT_EFFECTIVENESS_AUTHORITY["ai_can_certify_commitment_completion"] and not COMMITMENT_EFFECTIVENESS_AUTHORITY["worker_can_certify_closure"]
    ready=closure_readiness({"required_evidence_types":["control_test"]},[{"status":"completed"}],[{"evidence_type":"control_test","sha256":"a"*64,"status":"active"}],[{"independent":True,"result":"effective"}],[],[{"status":"acknowledged"}],[{"implemented":True}])
    sust=sustainability_state([{"days_since_closure":45,"health_score":95,"control_effective":True}],30)
    recurrence=recurrence_match({"control_id":"c","obligation_id":"o","normalized_theme":"data"},[{"signal_id":"s","control_id":"c","obligation_id":"o"}])
    return {"authority_boundary":authority,"closure_gate":ready["ready"],"sustainability":sust["state"]=="stable","recurrence_detection":bool(recurrence),"passed":authority and ready["ready"] and sust["state"]=="stable" and bool(recurrence)}
