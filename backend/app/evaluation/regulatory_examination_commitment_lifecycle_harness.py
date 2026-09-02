from app.domain.regulatory_examination_commitment_lifecycle import COMMITMENT_LIFECYCLE_AUTHORITY
from app.evaluation.regulatory_examination_commitment_lifecycle import completion_readiness,reconciliation_flags

def evaluate_release68()->dict:
    authority_ok=not COMMITMENT_LIFECYCLE_AUTHORITY["ai_can_certify_completion"] and not COMMITMENT_LIFECYCLE_AUTHORITY["worker_can_certify_completion"]
    ready=completion_readiness({"required_evidence_types":["control_test"]},[{"status":"completed"}],[{"evidence_type":"control_test","status":"active"}],[{"result":"effective"}])
    mismatch=reconciliation_flags({"commitment_id":"c","description":"A","due_at":"2026-10-01T00:00:00Z"},[{"commitment_id":"c","description":"B","due_at":"2026-10-02T00:00:00Z","reference":"r"}])
    return {"authority_boundary":authority_ok,"completion_gate":ready["ready"],"reconciliation_detection":len(mismatch)==2,"passed":authority_ok and ready["ready"] and len(mismatch)==2}
