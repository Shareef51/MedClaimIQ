from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"backend"))
from app.domain.regulatory_examination_reclosed_intervention_sustainability import RECLOSED_INTERVENTION_SUSTAINABILITY_AUTHORITY
from app.evaluation.regulatory_examination_reclosed_intervention_sustainability import multi_cycle_recurrence

def main():
    assert RECLOSED_INTERVENTION_SUSTAINABILITY_AUTHORITY["ai_can_reopen_or_reclose_program"] is False
    result=multi_cycle_recurrence({"cycles":[{"confirmed_recurrence":True,"intervention_effective":False},{"confirmed_recurrence":True,"intervention_effective":False}]})
    assert result["repeated_systemic_failure"] and result["executive_review_required"] and result["internal_audit_review_required"]
    print("Release 78 verification passed")
if __name__=="__main__": main()
