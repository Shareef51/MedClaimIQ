from app.services.regulatory_closure_governance import RegulatoryClosureGovernanceService

def evaluate_closure_readiness(case:dict)->dict:
    score=RegulatoryClosureGovernanceService.readiness_score(**case)
    return {"readiness_score":score,"ready":score==100,"closure_authority":"human_only"}

def evaluate_traceability(case:dict)->dict:
    required={"deficiency","corrective_action","retest","independent_validation","certification","sustainability"}
    present={k for k,v in case.items() if v}
    missing=sorted(required-present)
    return {"passed":not missing,"missing":missing}
