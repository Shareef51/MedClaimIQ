from app.evaluation.regulatory_submission_transport import evaluate

def test_release50_evaluation_dataset():
    r=evaluate();assert r=={"cases":5,"passed":5,"pass_rate":1.0,"authority_violations":0}
