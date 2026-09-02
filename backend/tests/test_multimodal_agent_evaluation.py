from app.evaluation.multimodal_agents import evaluate_multimodal_agent_contracts

def test_multimodal_agent_evaluation_passes():
    result=evaluate_multimodal_agent_contracts()
    assert result["passed"] is True
    assert result["value"]==1.0
