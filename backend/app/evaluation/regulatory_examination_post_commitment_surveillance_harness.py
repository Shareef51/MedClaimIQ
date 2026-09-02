from app.domain.regulatory_examination_post_commitment_surveillance import POST_COMMITMENT_SURVEILLANCE_AUTHORITY
from app.evaluation.regulatory_examination_post_commitment_surveillance import sustainability_decay, match_new_examination, cross_entity_recurrence

def evaluate_release70_scenario(closed_commitment:dict, observations:list[dict], findings:list[dict], entity_signals:list[dict])->dict:
    decay=sustainability_decay(observations)
    matches=match_new_examination(closed_commitment,findings)
    propagation=cross_entity_recurrence(entity_signals)
    return {"decay":decay,"examination_matches":matches,"cross_entity":propagation,"authority_safe":not POST_COMMITMENT_SURVEILLANCE_AUTHORITY["ai_can_reopen_commitment"] and not POST_COMMITMENT_SURVEILLANCE_AUTHORITY["worker_can_reopen_commitment"]}
