from app.domain.regulatory_examination_post_commitment_surveillance import POST_COMMITMENT_SURVEILLANCE_AUTHORITY
from app.evaluation.regulatory_examination_post_commitment_surveillance import sustainability_decay, match_new_examination, cross_entity_recurrence

def main():
    assert POST_COMMITMENT_SURVEILLANCE_AUTHORITY["ai_can_reopen_commitment"] is False
    assert sustainability_decay([{"days_since_closure":30,"health_score":95},{"days_since_closure":100,"health_score":70}])["reopen_candidate"] is True
    assert match_new_examination({"control_id":"c","obligation_id":"o"},[{"finding_id":"f","control_id":"c","obligation_id":"o"}])
    assert cross_entity_recurrence([{"entity_id":"A","recurrence_detected":True},{"entity_id":"B","control_effective":False}])["candidate"] is True
    print("Release 70 verification passed")
if __name__=="__main__": main()
