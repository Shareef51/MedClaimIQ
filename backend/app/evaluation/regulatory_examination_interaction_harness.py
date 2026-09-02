from app.domain.regulatory_examination_interaction import INTERACTION_AUTHORITY
from app.evaluation.regulatory_examination_interaction import detect_commitment_candidates,separate_positions

def evaluate_release67()->dict:
    sample=[{"statement_id":"s1","text":"We will provide the evidence by 2026-09-15","classification":"enterprise_statement"}]
    c=detect_commitment_candidates(sample)
    return {"authority_safe":not INTERACTION_AUTHORITY["ai_can_create_binding_commitment"],"candidate_detection":len(c)==1 and c[0]["binding"] is False,"position_separation":separate_positions([])=={"documented_regulator_positions":[],"enterprise_interpretations":[],"ai_observations":[]}}
