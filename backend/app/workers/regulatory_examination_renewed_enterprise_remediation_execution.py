from app.evaluation.regulatory_examination_renewed_enterprise_remediation_execution import critical_path_status, implementation_drift, effectiveness_kpis

def run_renewed_enterprise_remediation_monitor(items:list[dict])->dict:
    alerts=[]
    for item in items:
        cp=critical_path_status(item)
        drift=implementation_drift(item)
        kpi=effectiveness_kpis(item)
        if cp["critical_path_at_risk"] or drift["implementation_drift_detected"] or kpi["kpi_status"] != "on_track":
            alerts.append({"program_id":item.get("program_id"),"critical_path":cp,"drift":drift,"kpis":kpi,"monitoring_only":True})
    return {"alerts":alerts,"automated_approval":False,"automated_risk_acceptance":False,"automated_certification":False}
