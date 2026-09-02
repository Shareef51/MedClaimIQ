from app.domain.regulatory_examination_response import EXAM_RESPONSE_AUTHORITY
from app.evaluation.regulatory_examination_response import evidence_refresh_status,reconciliation_status

def evaluate_release66() -> dict:
    authority=(EXAM_RESPONSE_AUTHORITY["ai_can_approve_submission"] is False and EXAM_RESPONSE_AUTHORITY["ai_can_transmit_to_regulator"] is False)
    freshness=evidence_refresh_status([{"evidence_id":"E1","version":"1"}],{"E1":"1"})["fresh"]
    reconciliation=reconciliation_status({"human_approved":True},{"status":"acknowledged"},[])["reconciled"]
    return {"authority_boundary":authority,"evidence_freshness":freshness,"submission_reconciliation":reconciliation,"passed":all([authority,freshness,reconciliation])}
