from app.domain.regulatory_examination_reclosure_sustainability import RECLOSURE_SUSTAINABILITY_AUTHORITY
from app.evaluation.regulatory_examination_reclosure_sustainability import repeat_recurrence_score

def main():
    assert RECLOSURE_SUSTAINABILITY_AUTHORITY["ai_can_reopen_commitment"] is False
    x=repeat_recurrence_score([{"event_type":"recurrence"},{"event_type":"control_failure"},{"event_type":"reclosure_failure"}],3)
    assert x["third_occurrence"] and x["mandatory_internal_audit_review"]
    print("release72 verification: PASS")
if __name__=="__main__": main()
