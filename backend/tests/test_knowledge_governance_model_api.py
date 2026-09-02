from fastapi.testclient import TestClient
from app.main import app


def test_knowledge_governance_model_contract_is_public_and_states_authority_boundary():
    response = TestClient(app).get('/api/v1/knowledge-governance-model')
    assert response.status_code == 200
    body = response.json()
    assert 'Qdrant is a rebuildable projection' in body['authority']
    assert 'stale-vector-detection' in body['controls']
    assert body['retrieval_rule'].startswith('only promoted active')
