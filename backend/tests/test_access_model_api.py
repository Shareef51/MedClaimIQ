from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_access_model_is_deny_first_and_lists_roles() -> None:
    response = client.get("/api/v1/access-model")

    assert response.status_code == 200
    payload = response.json()
    assert payload["policy_id"] == "medclaimiq.authz.v1"
    assert payload["default_effect"] == "deny"
    assert "payer" in payload["tenant_types"]
    assert "explicit_cross_tenant_grants" in payload["principles"]

    roles = {item["role"]: item for item in payload["roles"]}
    assert "claims_reviewer" in roles
    assert "patient" in roles
    assert "tenant_admin" in roles
    assert "system_admin" in roles
    assert "claim:record_human_decision" in roles["claims_reviewer"]["permissions"]
    assert "claim:read" not in roles["system_admin"]["permissions"]
    assert "claim:read" not in roles["tenant_admin"]["permissions"]
