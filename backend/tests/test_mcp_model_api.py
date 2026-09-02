from fastapi.testclient import TestClient
from app.main import app


def test_mcp_model_contract_is_public_and_deny_by_default():
    response = TestClient(app).get("/api/v1/mcp-model")
    assert response.status_code == 200
    body = response.json()
    assert body["deny_by_default"] is True
    assert len(body["tools"]) == 6
    assert "human_approval" in body["controls"]
    assert "prompt_injection_screening" in body["controls"]


def test_openapi_exposes_stateless_mcp_transport_endpoint():
    schema = TestClient(app).get("/openapi.json").json()
    assert "/mcp" in schema["paths"]
    operation = schema["paths"]["/mcp"]["post"]
    assert "mcp-protocol" in operation["tags"]


def test_mcp_transport_requires_authentication_and_is_not_a_public_bypass():
    response = TestClient(app).post(
        "/mcp",
        headers={"MCP-Protocol-Version": "2026-07-28", "Mcp-Method": "server/discover"},
        json={"jsonrpc": "2.0", "id": 1, "method": "server/discover", "params": {}},
    )
    assert response.status_code == 401
