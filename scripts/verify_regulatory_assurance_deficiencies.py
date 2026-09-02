from app.domain.regulatory_assurance_deficiencies import regulatory_assurance_deficiency_contract
from app.evaluation.regulatory_assurance_deficiencies import evaluate_deficiency_aggregation

def main():
    c=regulatory_assurance_deficiency_contract();a=c["authority"]
    assert a["recommendation_only"] is True
    assert a["ai_can_declare_material_weakness"] is False
    assert a["human_closure_required"] is True
    r=evaluate_deficiency_aggregation([{"exception_id":"e1"},{"exception_id":"e2"}],[{"exception_ids":["e1","e2"]}])
    assert r["exception_to_deficiency_traceability"]==1.0
    print("Release 58 regulatory assurance deficiency verification: PASS")
if __name__=="__main__":main()
