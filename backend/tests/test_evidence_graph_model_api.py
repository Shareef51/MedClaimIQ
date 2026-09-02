from fastapi.testclient import TestClient
from app.main import app


def test_evidence_graph_model_endpoint_is_public_and_documents_safety():
    response = TestClient(app).get("/api/v1/evidence-graph-model")
    assert response.status_code == 200
    body = response.json()
    assert "claim_line" in body["canonical_entities"]
    assert "crosswalked_to" in body["relationships"]
    assert "deterministic" in body["safety"].lower()
    assert "tenant_id" in body["rag_metadata"]
