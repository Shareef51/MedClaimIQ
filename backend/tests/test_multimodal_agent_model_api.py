from fastapi.testclient import TestClient
from app.main import app

def test_public_multimodal_agent_model_contract():
    client=TestClient(app)
    response=client.get("/api/v1/multimodal-agent-orchestration-model")
    assert response.status_code==200
    body=response.json()
    assert body["architecture"]=="langgraph-multimodal-specialist-orchestration"
    assert "hospital_verification" in body["multimodal_agents"]
