from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"backend"))
from app.domain.regulatory_examination_enterprise_intervention_sustainability import ENTERPRISE_INTERVENTION_SUSTAINABILITY_AUTHORITY
from app.evaluation.regulatory_examination_enterprise_intervention_sustainability import intervention_closure_readiness

a=ENTERPRISE_INTERVENTION_SUSTAINABILITY_AUTHORITY
assert not a["ai_can_accept_residual_systemic_risk"] and not a["ai_can_close_intervention_program"]
r=intervention_closure_readiness({"implementation_complete":True,"independent_effectiveness_passed":True,"sustainability_assurance_passed":True,"cross_entity_reconciled":True,"regulatory_commitments_reconciled":True,"unresolved_blocker_count":0,"residual_risk_accepted_by_human":True})
assert r["closure_readiness_score"]==100 and r["ready_for_human_executive_closure"]
print("Release 75 enterprise intervention sustainability verification passed")
