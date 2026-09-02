from app.evaluation.regulatory_examination import evaluate_regulatory_examination
def test_release52_evaluation_has_zero_authority_violations():
    r=evaluate_regulatory_examination();assert r["cases"]==5 and r["passed"]==5 and r["pass_rate"]==1.0 and r["authority_violations"]==0
