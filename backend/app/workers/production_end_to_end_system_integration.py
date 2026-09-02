from app.evaluation.production_end_to_end_system_integration import release_candidate_readiness

def run_release_candidate_hardening_monitor(items: list[dict]) -> dict:
    assessments=[]
    for item in items:
        readiness=release_candidate_readiness(item)
        if not readiness["release_candidate_ready"]:
            assessments.append({"release_id":item.get("release_id"),"blocking_gates":readiness["blocking_gates"],"quality_score_failures":readiness["quality_score_failures"],"severity":"release_blocker"})
    return {"monitoring_only":True,"automated_release_candidate_declaration":False,"automated_production_promotion":False,"alerts":assessments}
