from fastapi.testclient import TestClient
from app.main import app

def test_evaluation_model_is_public_and_describes_gate():
    r=TestClient(app).get('/api/v1/evaluation-model'); assert r.status_code==200; body=r.json(); assert 'retrieval_recall_at_k' in body['metrics']; assert 'release' in body['release_gate']
