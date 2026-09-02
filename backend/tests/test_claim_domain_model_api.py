from fastapi.testclient import TestClient

from app.main import app


def test_claim_domain_model_exposes_non_sensitive_architecture_metadata() -> None:
    response = TestClient(app).get("/api/v1/claim-domain-model")

    assert response.status_code == 200
    body = response.json()
    assert "claim" in body["persisted_entities"]
    assert "evidence_lineage" in body["persisted_entities"]
    assert "postgresql_row_level_security" in body["database_isolation"]
    assert "human" in body["final_decision_boundary"].lower()
