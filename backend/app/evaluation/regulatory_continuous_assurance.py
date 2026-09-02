from __future__ import annotations

def evaluate_drift_detection(predicted:list[dict],actual:list[dict])->dict:
    p={(x.get("key"),x.get("severity")) for x in predicted};a={(x.get("key"),x.get("severity")) for x in actual}
    tp=len(p&a);precision=tp/len(p) if p else 1.0;recall=tp/len(a) if a else 1.0
    return {"precision":round(precision,4),"recall":round(recall,4),"false_positive_count":len(p-a),"missed_drift_count":len(a-p),"governance_checks":{"human_investigation_required_for_material_drift":True,"automatic_corrective_action":False,"automatic_finding_closure":False}}
