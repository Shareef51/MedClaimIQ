from pathlib import Path


def test_grounding_migration_has_rls_and_append_only_audit_tables():
    text = Path("alembic/versions/0011_rag_grounding_guardrails.py").read_text()
    for table in (
        "rag_guardrail_runs", "rag_prompt_injection_findings",
        "rag_statement_grounding_checks", "rag_guardrail_repair_attempts",
        "rag_human_review_escalations",
    ):
        assert table in text
    assert "ENABLE ROW LEVEL SECURITY" in text
    assert "FORCE ROW LEVEL SECURITY" in text
    assert "append_only" in text
    assert "immutable RAG guardrail audit record" in text
