from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"backend"))
from app.domain.regulatory_examination_systemic_recurrence_portfolio import SYSTEMIC_RECURRENCE_PORTFOLIO_AUTHORITY
from app.evaluation.regulatory_examination_systemic_recurrence_portfolio import aggregate_systemic_patterns, supervisory_materiality_score

def main():
    assert SYSTEMIC_RECURRENCE_PORTFOLIO_AUTHORITY["ai_can_approve_intervention_program"] is False
    a=aggregate_systemic_patterns([{"commitment_id":"1","root_cause_id":"r","entity_id":"a"},{"commitment_id":"2","root_cause_id":"r","entity_id":"b"},{"commitment_id":"3","root_cause_id":"r","entity_id":"c"}])
    assert a["systemic_pattern_candidate"]
    m=supervisory_materiality_score({"recurring_commitment_count":8,"affected_entity_count":8,"affected_control_count":6,"affected_examination_count":6,"regulator_count":3,"critical_control_count":4,"overdue_follow_up_count":3,"repeated_root_cause":True})
    assert m["enterprise_intervention_required"]
    print("Release 73 verification passed")
if __name__=="__main__": main()
