from app.evaluation.regulatory_examination_reclosed_recovery_surveillance import surveillance_score, examination_match_score, reopening_readiness

def monitor_reclosed_recovery(payload:dict)->dict:
    return {
        "monitoring_only": True,
        "surveillance": surveillance_score(payload.get("surveillance",{})),
        "examination_match": examination_match_score(payload.get("examination_match",{})),
        "reopening_readiness": reopening_readiness(payload.get("reopening_readiness",{})),
        "automated_reopening": False,
        "automated_reclosure": False,
        "automated_residual_risk_acceptance": False,
        "automated_recovery_certification": False,
    }
