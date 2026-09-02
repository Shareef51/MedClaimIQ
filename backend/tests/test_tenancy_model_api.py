from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_tenancy_model_exposes_non_sensitive_architecture_metadata() -> None:
    response = client.get("/api/v1/tenancy-model")

    assert response.status_code == 200
    body = response.json()
    assert "postgresql_row_level_security" in body["isolation_strategy"]
    assert "resource_grant" in body["persisted_entities"]
    assert body["tenant_context"].endswith("app.current_tenant_id")
