from app.evaluation.regulatory_remediation import evaluate_regulatory_remediation

def test_regulatory_remediation_evaluation_has_zero_authority_violations():
    r=evaluate_regulatory_remediation();assert r["cases"]==5 and r["passed"]==5 and r["authority_violations"]==0
