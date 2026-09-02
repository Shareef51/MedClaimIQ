from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"backend"))
from app.domain.regulatory_examination_enterprise_intervention_execution import ENTERPRISE_INTERVENTION_EXECUTION_AUTHORITY
from app.evaluation.regulatory_examination_enterprise_intervention_execution import program_execution_readiness, effectiveness_assurance

def main():
    assert ENTERPRISE_INTERVENTION_EXECUTION_AUTHORITY["ai_can_certify_effectiveness"] is False
    r=program_execution_readiness({"workstreams":[{"status":"completed"}],"dependencies":[],"checkpoints":[{"evidence_complete":True}],"required_entity_ids":["US"],"validated_entity_ids":["US"],"regulatory_commitment_links":[{"mapped":True}]})
    assert r["ready_for_independent_assurance"]
    a=effectiveness_assurance({"independent_tests":[{"entity_id":"US","result":"pass"}],"required_entity_ids":["US"],"residual_systemic_risk_score":10})
    assert a["eligible_for_human_executive_certification"]
    print("Release 74 enterprise intervention execution verification: PASS")
if __name__=="__main__": main()
