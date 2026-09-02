from fastapi.testclient import TestClient
from app.main import app


def test_cross_source_rag_model_documents_safe_structured_and_graph_retrieval():
    response = TestClient(app).get("/api/v1/cross-source-rag-model")
    assert response.status_code == 200
    body = response.json()
    assert body["structured_query_safety"]["arbitrary_sql_generation"] is False
    assert body["graph_rag"]["arbitrary_graph_query_generation"] is False
    assert body["graph_rag"]["claim_scoped"] is True
    assert "immutable evidence-pack snapshots for downstream agents" in body["fusion"]
