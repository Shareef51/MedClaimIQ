from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
required=[
 "backend/app/domain/financial_handoff.py","backend/app/models/financial_handoff.py","backend/app/services/financial_handoff.py","backend/app/api/v1/financial_handoff.py","backend/app/financial/adapters.py","backend/app/workers/financial_handoff.py","backend/alembic/versions/0035_financial_handoff_reconciliation.py","frontend/app/review/financial/page.tsx","config/financial_handoff.yaml","docs/CONTROLLING_DECISION_FINANCIAL_HANDOFF.md"
]
missing=[x for x in required if not (ROOT/x).exists()]
assert not missing,missing
service=(ROOT/"backend/app/services/financial_handoff.py").read_text()
domain=(ROOT/"backend/app/domain/financial_handoff.py").read_text()
migration=(ROOT/"backend/alembic/versions/0035_financial_handoff_reconciliation.py").read_text()
adapter=(ROOT/"backend/app/financial/adapters.py").read_text()
for token in ["decision_history_sha256","evidence_snapshot_sha256","locked_payload_sha256","authorized_payload_sha256","payment_fingerprint","active fraud/payment hold","segregation of duties","settled_amount_mismatch","void/reissue"]: assert token in service,token
for token in ['"llm_can_authorize_funds": False','"langgraph_can_authorize_funds": False','"rag_can_authorize_funds": False','"mcp_can_authorize_funds": False','"background_worker_can_authorize_funds": False','"automatic_fund_movement": False']: assert token in domain,token
assert "never moves funds" in adapter
assert "ENABLE ROW LEVEL SECURITY" in migration and "FORCE ROW LEVEL SECURITY" in migration and "reject_locked_financial_packet_mutation" in migration
# Autonomous AI/tool directories must not call the human finance authorization method.
for rel in ["backend/app/agents","backend/app/orchestration","backend/app/rag","backend/app/mcp"]:
    d=ROOT/rel
    if d.exists():
        for p in d.rglob("*.py"):
            text=p.read_text(errors="ignore")
            assert ".authorize_packet(" not in text, f"unauthorized finance authorization path in {p}"
print("controlling-decision financial handoff verifier: PASS")

worker=(ROOT/"backend/app/workers/financial_handoff.py").read_text()
assert "ready_for_handoff" in worker and "authorize_packet" not in worker
helm=(ROOT/"infra/helm/medclaimiq/values.yaml").read_text()
assert "financial-handoff:" in helm and "FINANCIAL_SETTLEMENT_WEBHOOK_SECRET" in helm
