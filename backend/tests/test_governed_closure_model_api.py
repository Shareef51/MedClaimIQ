from fastapi.testclient import TestClient
from app.main import app


def test_public_governed_closure_model_is_human_only_and_concurrency_safe():
    body=TestClient(app).get('/api/v1/governed-closure-model').json()
    assert body['human_authority']['authenticated_human_reviewer_required'] is True
    assert body['human_authority']['llm_final_decision'] is False
    assert body['human_authority']['langgraph_final_decision'] is False
    assert body['human_authority']['rag_final_decision'] is False
    assert body['human_authority']['mcp_final_decision'] is False
    assert body['human_authority']['automated_financial_adjudication'] is False
    assert body['concurrency']['exclusive_primary_reviewer_lease'] is True
    assert body['concurrency']['optimistic_packet_version'] is True
    assert body['governance']['immutable_hash_chained_audit'] is True
