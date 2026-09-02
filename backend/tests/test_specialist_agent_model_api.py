from fastapi.testclient import TestClient
from app.main import app


def test_specialist_agent_model_contract_is_public_and_safety_scoped():
    response = TestClient(app).get("/api/v1/specialist-agent-model")
    assert response.status_code == 200
    body = response.json()
    assert len(body["agents"]) == 13
    assert body["structured_outputs"]["strict_json_schema"] is True
    assert body["tool_policy"]["database_mutation_tools"] is False
    assert body["evidence_boundary"]["unknown_evidence_key_rejected"] is True
