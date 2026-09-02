from app.evaluation.production_performance_resilience_disaster_recovery_operational_readiness import operational_go_live_readiness

def run_operational_readiness_monitor(items:list[dict])->dict:
    alerts=[]
    for item in items:
        r=operational_go_live_readiness(item)
        if not r["operational_go_live_ready"]:
            alerts.append({"release_id":item.get("release_id"),"blocking_gates":r["blocking_gates"],"non_bypassable_operational_risks":r["non_bypassable_operational_risks"],"severity":"operational_go_live_blocker"})
    return {"monitoring_only":True,"automated_operational_risk_acceptance":False,"automated_operational_certification":False,"automated_production_promotion":False,"alerts":alerts}
