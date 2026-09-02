from fastapi.testclient import TestClient
from app.main import app


def test_public_multimodal_review_model_keeps_human_decision_boundary():
    body=TestClient(app).get('/api/v1/multimodal-review-model').json()
    assert body['safety']['final_claim_decision_is_human_only'] is True
    assert body['safety']['signed_media_access_is_claim_scoped'] is True
    assert 'frame_sha256' in body['viewer']['video']
    assert 'fhir_version_id' in body['viewer']['fhir']
