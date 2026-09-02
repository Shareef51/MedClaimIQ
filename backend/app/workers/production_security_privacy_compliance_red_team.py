from app.evaluation.production_security_privacy_compliance_red_team import security_release_readiness

def run_release_security_monitor(items:list[dict])->dict:
    alerts=[]
    for item in items:
        r=security_release_readiness(item)
        if not r["release_security_ready"]:
            alerts.append({"release_id":item.get("release_id"),"blocking_gates":r["blocking_gates"],"critical_high":r["open_critical_high_findings"],"nonwaivable":r["open_nonwaivable_findings"],"severity":"release_security_blocker"})
    return {"monitoring_only":True,"automated_security_waiver_approval":False,"automated_security_certification":False,"automated_production_promotion":False,"alerts":alerts}
