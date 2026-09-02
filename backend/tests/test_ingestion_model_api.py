from fastapi.testclient import TestClient

from app.main import app


def test_ingestion_model_exposes_quarantine_guardrail() -> None:
    response = TestClient(app).get("/api/v1/ingestion-model")
    assert response.status_code == 200
    payload = response.json()
    assert "pdf" in payload["supported_media_kinds"]
    assert "video" in payload["supported_media_kinds"]
    assert "No OCR" in payload["acceptance_rule"]
    assert any("magic-byte" in item for item in payload["validation_controls"])
