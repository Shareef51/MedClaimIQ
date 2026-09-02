from fastapi.testclient import TestClient
from app.main import app


def test_rag_model_endpoint_is_public_and_documents_domains_and_security():
    response = TestClient(app).get("/api/v1/rag-model")
    assert response.status_code == 200
    body = response.json()
    assert set(body["domains"]) == {"claim", "policy", "hospital", "invoice", "coding", "historical_claims", "evidence"}
    assert body["indexing"]["vector_projection"] == "Qdrant domain collections"
    assert "tenant" in body["safety"].lower()
    assert body["embeddings"]["default_model"] == "text-embedding-3-large"
