from app.evaluation.production_go_live_governance_final_release_certification import final_go_live_readiness, assess_hypercare

def run_final_go_live_monitor(items:list[dict])->dict:
    alerts=[]
    for item in items:
        r=final_go_live_readiness(item)
        if not r["final_go_live_ready"]: alerts.append({"release_id":item.get("release_id"),"type":"go_live_blocked","blockers":r["missing_final_gates"]+r["non_bypassable_open_risks"]})
        h=item.get("hypercare")
        if h:
            a=assess_hypercare(h)
            if a["open_sev1"] or not a["command_center_ready"]: alerts.append({"release_id":item.get("release_id"),"type":"hypercare_escalation"})
    return {"monitoring_only":True,"alerts":alerts,"automated_go_live_approval":False,"automated_production_promotion":False,"automated_final_certification":False,"automated_hypercare_closure":False}
