from fastapi.testclient import TestClient

from app.main import app


def test_orchestration_model_exposes_end_to_end_execution_and_sse_contract():
    response = TestClient(app).get("/api/v1/agent-orchestration-model")
    assert response.status_code == 200
    body = response.json()
    assert body["execution_engine"]["specialist_failure_isolation"] is True
    assert body["execution_engine"]["evidence_pack_rehydration_hash_check"] is True
    assert body["streaming"]["transport"] == "SSE"
    assert body["human_in_the_loop"]["interrupt_resume"] is True
