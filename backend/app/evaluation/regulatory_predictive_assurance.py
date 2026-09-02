from __future__ import annotations
def evaluate_predictive_forecast(predicted:dict,actual:dict)->dict:
    keys=["remediation_failure_risk","deadline_breach_risk","recurrence_risk","control_deterioration_risk"]
    errors={k:abs(float(predicted.get(k,0))-float(actual.get(k,0))) for k in keys}
    return {"mae":round(sum(errors.values())/len(keys),3),"by_metric":errors,"governance_checks":{"human_review_required":True,"automatic_regulatory_action":False}}
