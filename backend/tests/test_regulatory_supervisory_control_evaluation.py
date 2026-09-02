from app.evaluation.regulatory_supervisory_control import evaluate_regulatory_supervision

def test_release51_evaluation_dataset_has_zero_authority_violations():
    result=evaluate_regulatory_supervision();assert result=={"cases":5,"passed":5,"pass_rate":1.0,"authority_violations":0}
