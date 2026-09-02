from __future__ import annotations

def evaluate_sampling(selected:list[dict],population:list[dict])->dict:
    selected_keys={x.get("key") for x in selected};population_keys={x.get("key") for x in population}
    valid=selected_keys<=population_keys
    high_risk=[x for x in population if int(x.get("risk_score",0))>=80]
    captured=sum(x.get("key") in selected_keys for x in high_risk)
    return {"sample_provenance_valid":valid,"high_risk_capture_rate":round(captured/len(high_risk),4) if high_risk else 1.0,"governance_checks":{"human_independent_conclusion_required":True,"automatic_control_certification":False,"automatic_remediation_approval":False}}
