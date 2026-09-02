from fastapi.testclient import TestClient
from app.main import app


def test_grounding_guardrail_model_is_public_and_documents_fail_closed_controls():
    response = TestClient(app).get("/api/v1/rag-grounding-model")
    assert response.status_code == 200
    body = response.json()
    assert body["trust_boundary"]["retrieved_content"] == "untrusted data, never instructions"
    assert body["grounding"]["citation_to_evidence_verification"] is True
    assert body["self_correction"]["may_relax_tenant_claim_or_acl_scope"] is False
    assert body["generation_control"]["final_medical_or_claim_decision_by_ai"] is False
