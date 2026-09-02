from __future__ import annotations
from decimal import Decimal
from app.services.accounting_ledger import AccountingLedgerService
from app.services.financial_intelligence import FinancialIntelligenceService
from app.models.financial_intelligence import ClaimReserveSnapshotModel, FinancialAnalyticsSnapshotModel, FinancialCopilotRunModel
from tests.test_accounting_ledger import paid_intent
from tests.test_appeal_evidence_reconsideration import factory

def _reconciled(db,key="intel"):
    i=paid_intent(db,key);acct=AccountingLedgerService(db,"tenant-a")
    acct.record_era("claim-1",i.payment_intent_id,"finance-op",era_reference=f"ERA-{key}",payment_reference=f"REF-{key}",provider_ref="provider:org-a",paid_amount=Decimal("1000"))
    acct.record_eft("claim-1",i.payment_intent_id,"finance-op",eft_reference=f"EFT-{key}",bank_reference=f"REF-{key}",trace_number=f"TRACE-{key}",amount=Decimal("1000"))
    acct.reconcile("claim-1",i.payment_intent_id,"finance-op",idempotency_key=f"recon-{key}")
    return i,acct

def test_claim_reserve_paid_vs_incurred_and_immutable_snapshot_tracking():
    f=factory()
    with f() as db:
        i=paid_intent(db,"reserve");svc=FinancialIntelligenceService(db,"tenant-a")
        before=svc.claim_analytics("claim-1");assert before["metrics"]["approved_incurred"]=="1000.00" and before["metrics"]["net_paid"]=="0.00" and before["metrics"]["outstanding_reserve"]=="1000.00"
        acct=AccountingLedgerService(db,"tenant-a");acct.record_era("claim-1",i.payment_intent_id,"finance-op",era_reference="ERA-reserve",payment_reference="REF-reserve",provider_ref="provider:org-a",paid_amount=Decimal("1000"));acct.record_eft("claim-1",i.payment_intent_id,"finance-op",eft_reference="EFT-reserve",bank_reference="REF-reserve",trace_number="TRACE-reserve",amount=Decimal("1000"));acct.reconcile("claim-1",i.payment_intent_id,"finance-op",idempotency_key="recon-reserve")
        after=svc.claim_analytics("claim-1");assert after["metrics"]["net_paid"]=="1000.00" and after["metrics"]["outstanding_reserve"]=="0.00"
        history=after["reserve_history"];assert len(history)==2 and history[-1]["reserve_variance"]=="-1000.00"
        assert db.query(ClaimReserveSnapshotModel).count()==2 and db.query(FinancialAnalyticsSnapshotModel).filter_by(scope_type="claim").count()==2

def test_returned_payment_surfaces_leakage_anomaly_and_explainable_investigation():
    f=factory()
    with f() as db:
        i,acct=_reconciled(db,"returnintel");acct.record_return("claim-1",i.payment_intent_id,"finance-op",return_reference="RET-intel",return_code="R01",amount=Decimal("250"),reason="Bank return creates renewed claim-payment exposure and requires human accounting follow-up.")
        svc=FinancialIntelligenceService(db,"tenant-a");data=svc.claim_analytics("claim-1")
        assert data["metrics"]["net_paid"]=="750.00" and data["metrics"]["outstanding_reserve"]=="250.00" and data["metrics"]["financial_leakage_exposure"]=="250.00"
        assert any(x["factor"]=="returned_payment" for x in data["anomaly_factors"])
        inv=svc.investigate("claim-1","finance-op","returned_payment");assert inv["authority"]=={"adjudication":"none","accounting":"none","fund_movement":"none"} and inv["citations"] and "read-only" in inv["explanation"]

def test_portfolio_kpis_provider_patterns_recoupment_aging_and_close_readiness():
    f=factory()
    with f() as db:
        i,acct=_reconciled(db,"portfolio")
        a=acct.request_adjustment("claim-1",i.payment_intent_id,"finance-op",adjustment_type="recoupment",amount=Decimal("125"),reason_code="provider_overpayment",rationale="Governed recoupment request remains pending human finance approval and should appear in intelligence aging.",idempotency_key="intel-recoup")
        svc=FinancialIntelligenceService(db,"tenant-a");p=svc.portfolio("finance-op")
        assert p["kpis"]["claims_analyzed"]>=1 and Decimal(p["kpis"]["incurred_amount"])>=Decimal("1000")
        assert p["provider_patterns"] and p["provider_patterns"][0]["provider_ref"]=="provider:org-a"
        assert any(x["adjustment_id"]==a.adjustment_id for x in p["recoupment_aging"])
        assert p["period_close_readiness"] and p["period_close_readiness"][0]["readiness_score"]<100

def test_financial_rag_copilot_is_cited_and_has_zero_authority():
    f=factory()
    with f() as db:
        _reconciled(db,"copilot");svc=FinancialIntelligenceService(db,"tenant-a")
        r=svc.copilot("finance-op","What is the paid amount and outstanding reserve for claim-1?",claim_id="claim-1")
        assert r["citations"] and any(c["type"] in {"financial_authorization_packet","era_eft_reconciliation","immutable_ledger_journal","claim_financial_analytics"} for c in r["citations"])
        assert r["authority"]=={"adjudication":"none","accounting":"none","fund_movement":"none"}
        assert "cannot modify journals, reserves, payment authorization" in r["answer"]
        row=db.get(FinancialCopilotRunModel,r["run_id"]);assert row and row.accounting_authority=="none" and row.fund_movement_authority=="none"

def test_release42_source_authority_contract_is_fail_closed():
    from pathlib import Path
    root=Path(__file__).resolve().parents[2];domain=(root/'backend/app/domain/financial_intelligence.py').read_text();worker=(root/'backend/app/workers/financial_intelligence.py').read_text();migration=(root/'backend/alembic/versions/0037_financial_intelligence_read_model.py').read_text()
    for token in ['"llm_can_modify_ledger": False','"rag_can_modify_ledger": False','"ai_can_modify_reserve": False','"ai_can_authorize_payment": False','"ai_can_close_accounting_period": False','"automatic_fund_movement": False']:assert token in domain
    for forbidden in ['_post_journal(', 'close_period(', 'authorize_packet(', 'approve_adjustment(', 'handoff(', 'request_adjustment(']:assert forbidden not in worker
    assert 'ENABLE ROW LEVEL SECURITY' in migration and 'FORCE ROW LEVEL SECURITY' in migration and 'reject_financial_intelligence_snapshot_mutation' in migration

def test_optional_model_assisted_financial_copilot_remains_grounded_and_read_only():
    import json
    from types import SimpleNamespace
    from app.services.financial_intelligence import FinancialCopilotSynthesis
    class FakeModel:
        def generate(self,*,model,instructions,input_text,schema):
            evidence=json.loads(input_text)["evidence"]
            parsed=FinancialCopilotSynthesis(answer="The governed financial evidence shows a fully reconciled payment.",cited_ids=[evidence[0]["citation_id"]],recommendations=["Human finance analyst may review the cited ledger record if additional investigation is needed."])
            return SimpleNamespace(parsed=parsed,model=model,response_id="resp-test",input_tokens=10,output_tokens=8)
    f=factory()
    with f() as db:
        _reconciled(db,"modelcopilot");svc=FinancialIntelligenceService(db,"tenant-a",model_client=FakeModel(),copilot_model="gpt-test")
        r=svc.copilot("finance-op","Explain the reconciled payment with citations",claim_id="claim-1")
        assert "fully reconciled payment" in r["answer"] and r["citations"] and r["authority"]["fund_movement"]=="none"
        assert "recommendation-only" in r["answer"]
