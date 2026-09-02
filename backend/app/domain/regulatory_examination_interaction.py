from __future__ import annotations

INTERACTION_AUTHORITY = {
    "recommendation_only": True,
    "ai_can_summarize_meetings": True,
    "ai_can_extract_candidate_commitments": True,
    "ai_can_detect_response_contradictions": True,
    "ai_can_create_binding_commitment": False,
    "ai_can_represent_regulator_intent": False,
    "worker_can_confirm_commitment": False,
    "human_confirmation_required": True,
    "accounting_mutation_allowed": False,
    "payment_authority_allowed": False,
}
SESSION_STATUSES=("scheduled","in_progress","completed","minutes_under_review","finalized")
COMMITMENT_STATUSES=("candidate","human_review","confirmed","rejected","in_progress","completed","overdue")

def examination_interaction_contract()->dict:
    return {
        "name":"production_regulatory_examination_interaction_governance_supervisory_meeting_intelligence_and_commitment_capture_assurance",
        "capabilities":["meeting_session_registry","agenda_attendee_governance","examiner_question_capture","meeting_note_provenance","transcript_evidence_linkage","ai_assisted_summary","regulator_position_enterprise_interpretation_separation","verbal_commitment_candidate_detection","human_commitment_confirmation","action_owner_due_date_governance","prior_submission_contradiction_checks","follow_up_evidence_requests","meeting_to_finding_linkage","immutable_interaction_timeline","sse_alerts","audit_exports"],
        "session_statuses":SESSION_STATUSES,
        "commitment_statuses":COMMITMENT_STATUSES,
        "authority":INTERACTION_AUTHORITY,
        "traceability":"regulator interaction -> evidence -> captured statement -> human validation -> commitment/action -> follow-up -> examination record",
    }
