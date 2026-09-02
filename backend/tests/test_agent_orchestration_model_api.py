from fastapi.testclient import TestClient
from app.main import app


def test_agent_orchestration_model_is_public_and_documents_safety_boundary():
    response = TestClient(app).get("/api/v1/agent-orchestration-model")
    assert response.status_code == 200
    body = response.json()
    assert body["framework"] == "LangGraph 1.x"
    assert body["durability"]["checkpoint_store"] == "PostgreSQL LangGraph checkpointer"
    assert body["routing"]["parallel_fan_out"] is True
    assert body["human_in_the_loop"]["interrupt_resume"] is True
    assert any("cannot finalize claims" in item for item in body["safety_boundaries"])
