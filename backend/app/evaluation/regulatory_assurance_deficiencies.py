from __future__ import annotations

def evaluate_deficiency_aggregation(exceptions:list[dict],deficiencies:list[dict])->dict:
    known={x.get("exception_id") for x in exceptions}; linked={eid for d in deficiencies for eid in d.get("exception_ids",[])}
    coverage=round(len(known & linked)/len(known),4) if known else 1.0
    return {"exception_to_deficiency_traceability":coverage,"unlinked_exception_count":len(known-linked),"governance_checks":{"ai_material_weakness_declaration":False,"human_independent_escalation_required":True,"human_closure_required":True,"automatic_risk_acceptance":False}}
