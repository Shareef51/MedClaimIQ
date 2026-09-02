from pathlib import Path

required = [
    "backend/app/domain/grounding.py",
    "backend/app/guardrails/prompt_injection.py",
    "backend/app/guardrails/citations.py",
    "backend/app/guardrails/statement_grounding.py",
    "backend/app/guardrails/answerability.py",
    "backend/app/guardrails/prompt_envelope.py",
    "backend/app/services/grounding.py",
    "backend/app/api/v1/grounding.py",
    "backend/alembic/versions/0011_rag_grounding_guardrails.py",
    "backend/app/models/grounding.py",
    "config/rag_grounding_guardrails_policy.json",
]
missing = [item for item in required if not Path(item).exists()]
assert not missing, f"missing grounding guardrail artifacts: {missing}"
service = Path("backend/app/services/grounding.py").read_text()
scanner = Path("backend/app/guardrails/prompt_injection.py").read_text()
assert "max_repairs must be between 0 and 2" in service
assert "requested_retrievers=repair_retrievers" in service
assert "exclude_from_model_context" in scanner
assert "GuardrailDecision.BLOCK" in service
print("RAG grounding guardrail architecture verified")
