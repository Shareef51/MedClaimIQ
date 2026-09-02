from __future__ import annotations
from app.evaluation.regulatory_examination_response import sla_risk

def monitor_exam_response_queue(items:list[dict]) -> list[dict]:
    """Monitoring-only worker: emits escalation candidates; never approves or transmits."""
    events=[]
    for item in items:
        risk=sla_risk(float(item.get("due_in_hours",9999)),int(item.get("unresolved_dependencies",0)),bool(item.get("review_pending",False)))
        if risk["level"] in {"high","critical"}:
            events.append({"event":"regulatory.exam_response.sla_at_risk","question_id":item.get("question_id"),"risk":risk,"action":"human_review_required"})
    return events
