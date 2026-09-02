from fastapi.testclient import TestClient

from app.main import app


def test_rag_model_documents_hybrid_retrieval_and_no_evidence():
    body = TestClient(app).get("/api/v1/rag-model").json()
    foundation = " ".join(body["retrieval_foundation"]).lower()
    assert "hybrid" in foundation
    assert "reciprocal-rank" in foundation
    assert "no-evidence" in foundation
    assert "telemetry" in foundation
