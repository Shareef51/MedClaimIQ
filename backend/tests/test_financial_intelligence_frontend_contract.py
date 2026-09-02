from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def test_release42_frontend_bff_config_telemetry_and_worker_contract():
    page=(ROOT/'frontend/app/review/financial-intelligence/page.tsx').read_text();api=(ROOT/'frontend/lib/api.ts').read_text();bff=(ROOT/'frontend/app/api/reviewer/[...path]/route.ts').read_text();config=(ROOT/'config/financial_intelligence.yaml').read_text();metrics=(ROOT/'backend/app/observability/metrics.py').read_text();worker=(ROOT/'backend/app/workers/financial_intelligence.py').read_text();runtime=(ROOT/'backend/app/workers/production_runtime.py').read_text();values=(ROOT/'infra/helm/medclaimiq/values.yaml').read_text()
    for token in ['Reserve, Payment Integrity','Provider payment-pattern intelligence','Accounting close readiness','Accounting control exceptions','Explainable anomaly factors','Financial RAG / Copilot','Ledger citation drill-down','Read-only authority boundary']:assert token in page
    assert 'financialIntelligenceClaim' in api and 'financialIntelligencePortfolio' in api and 'financialCopilot' in api
    assert 'financial-intelligence' in bff and 'structured_ledger_hybrid_lexical_citation_retrieval_v1' in config
    assert 'record_financial_intelligence' in metrics
    assert 'financial-intelligence' in runtime and 'financial-intelligence:' in values and 'FINANCIAL_INTELLIGENCE_COPILOT_MODEL_ENABLED' in values
    for forbidden in ['_post_journal(', 'close_period(', 'authorize_packet(', 'approve_adjustment(', 'handoff(']:assert forbidden not in worker
