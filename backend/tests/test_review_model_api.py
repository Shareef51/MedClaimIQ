from fastapi.testclient import TestClient
from app.main import app

def test_review_model_contract():
    r=TestClient(app).get('/api/v1/review-model')
    assert r.status_code == 200
    body=r.json()
    assert body['concurrency']['lease_lock'] is True
    assert body['human_authority']['final_decision_only_by_authorized_reviewer'] is True
    assert body['human_authority']['ai_recommendation_is_advisory'] is True
