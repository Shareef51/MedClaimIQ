from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
required=[
"backend/app/observability/tracing.py","backend/app/observability/redaction.py","backend/app/models/llmops.py",
"backend/app/services/llmops.py","backend/app/api/v1/llmops.py","config/llmops_policy.json","docs/LLMOPS_OBSERVABILITY.md"
]
missing=[x for x in required if not (ROOT/x).exists()]
if missing: raise SystemExit(f"missing LLMOps artifacts: {missing}")
text=(ROOT/"backend/app/observability/redaction.py").read_text()
for token in ("prompt","evidence_text","access_token","refresh_token"):
    assert token in text
print("LLMOps observability architecture verified")
