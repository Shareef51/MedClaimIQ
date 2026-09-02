from __future__ import annotations
from decimal import Decimal
from pathlib import Path
from app.services.recovery_settlement import RecoverySettlementService
from app.services.recovery_settlement_intelligence import RecoverySettlementIntelligenceService
from tests.test_recovery_settlement import factory,release46_final,settlement_journal

def setup_case(db,key="p48",target=Decimal("100")):
    _,recovery,_,_=release46_final(db,key,target);svc=RecoverySettlementService(db,"tenant-a");case=svc.create_from_recovery(recovery.recovery_case_id,"finance-op",idempotency_key=f"{key}-settlement");return svc,case

def test_immutable_provider_balance_statement_versions_follow_source_watermarks_without_mutating_release47_balance():
    f=factory()
    with f() as db:
        rs,c=setup_case(db,"statement48");intel=RecoverySettlementIntelligenceService(db,"tenant-a")
        before=(c.target_amount,c.verified_amount,c.remaining_amount,c.case_version);s1=intel.provider_statement("org-a","finance-op");assert s1["statement_version"]==1 and s1["remaining_balance"]=="100.00" and len(s1["payload_sha256"])==64
        assert (c.target_amount,c.verified_amount,c.remaining_amount,c.case_version)==before
        e=rs.submit_evidence(c.settlement_case_id,"provider-user",evidence_type="bank_repayment",amount=Decimal("40"),currency="USD",installment_sequence=1,external_reference="P48-BANK-1",bank_reference="P48-BANK-1",remittance_reference=None,provider_reference="org-a",evidence_refs=[],occurred_at=None,idempotency_key="p48-stmt-e")
        rs.verify_evidence(c.settlement_case_id,e.settlement_evidence_id,"finance-op",reference_match=True,verification_rationale="Human finance operator verifies the external repayment reference before settlement intelligence observes it.",expected_case_version=2,idempotency_key="p48-stmt-v")
        s2=intel.provider_statement("org-a","finance-op");assert s2["statement_version"]==2 and s2["remaining_balance"]=="60.00" and s2["payload_sha256"]!=s1["payload_sha256"]
        assert len(intel.repo.statements("org-a"))==2

def test_under_over_recovery_aging_and_exception_investigation_are_explainable_and_read_only():
    f=factory()
    with f() as db:
        rs,c=setup_case(db,"over48");e=rs.submit_evidence(c.settlement_case_id,"provider-user",evidence_type="bank_repayment",amount=Decimal("120"),currency="USD",installment_sequence=1,external_reference="P48-OVER",bank_reference="P48-OVER",remittance_reference=None,provider_reference="org-a",evidence_refs=[],occurred_at=None,idempotency_key="p48-over-e");rs.verify_evidence(c.settlement_case_id,e.settlement_evidence_id,"finance-op",reference_match=True,verification_rationale="Human finance operator verifies an external repayment amount that exceeds the governed recovery target and creates a Release 47 exception.",expected_case_version=2,idempotency_key="p48-over-v")
        intel=RecoverySettlementIntelligenceService(db,"tenant-a");p=intel.portfolio("finance-op");assert p["kpis"]["over_recovery_amount"]=="20.00" and any(x.get("code")=="over_recovery" for x in p["settlement_exceptions"])
        inv=intel.investigate_exception(c.settlement_case_id,"finance-op","over_recovery");assert inv["authority"]=={"accounting":"none","fund_movement":"none"} and inv["citations"] and "does not alter balances" in inv["explanation"]

def test_human_released_provider_statement_delivery_is_portal_visible_but_does_not_change_balance():
    f=factory()
    with f() as db:
        _,c=setup_case(db,"delivery48");intel=RecoverySettlementIntelligenceService(db,"tenant-a");s=intel.provider_statement("org-a","finance-op");before=(c.target_amount,c.verified_amount,c.remaining_amount,c.case_version)
        d=intel.publish_statement(s["statement_id"],"finance-approver",idempotency_key="p48-publish");same=intel.publish_statement(s["statement_id"],"finance-approver",idempotency_key="p48-publish-repeat");assert d.delivery_id==same.delivery_id and d.channel=="portal"
        portal=intel.provider_portal_statements("provider-user");assert len(portal)==1 and portal[0]["statement_id"]==s["statement_id"] and portal[0]["delivery_payload_sha256"]
        assert (c.target_amount,c.verified_amount,c.remaining_amount,c.case_version)==before

def test_closeout_report_binds_human_certificate_accounting_period_and_journal_citations():
    f=factory()
    with f() as db:
        rs,c=setup_case(db,"report48");e=rs.submit_evidence(c.settlement_case_id,"provider-user",evidence_type="bank_repayment",amount=Decimal("100"),currency="USD",installment_sequence=1,external_reference="P48-FULL",bank_reference="P48-FULL",remittance_reference=None,provider_reference="org-a",evidence_refs=[],occurred_at=None,idempotency_key="p48-full-e");rs.verify_evidence(c.settlement_case_id,e.settlement_evidence_id,"finance-op",reference_match=True,verification_rationale="Human finance operator verifies exact repayment evidence before accounting correlation.",expected_case_version=2,idempotency_key="p48-full-v")
        j=settlement_journal(db,Decimal("100"),"p48-journal");rs.correlate_ledger(c.settlement_case_id,e.settlement_evidence_id,"finance-op",journal_id=j.journal_id,amount=Decimal("100"),currency="USD",idempotency_key="p48-correlation");current=rs.repo.case(c.settlement_case_id);cert=rs.prepare_certificate(c.settlement_case_id,"finance-op",accounting_period_id=j.period_id,reason_codes=["external_repayment_verified","ledger_reconciled"],rationale="Human finance operator prepares financial closeout only after exact external repayment and immutable ledger correlation.",expected_case_version=current.case_version,idempotency_key="p48-cert");current=rs.repo.case(c.settlement_case_id);rs.decide_certificate(c.settlement_case_id,cert.certificate_id,"finance-approver-2",action="approve",rationale="Independent human finance approver certifies exact financial closeout evidence and accounting-period linkage.",expected_case_version=current.case_version,idempotency_key="p48-cert-approve")
        intel=RecoverySettlementIntelligenceService(db,"tenant-a");r=intel.accounting_closeout_report(j.period_id,"finance-op");assert r["certificate_count"]==1 and r["certificates"][0]["certificate_sha256"]==cert.payload_sha256 and len(r["manifest_sha256"])==64

def test_settlement_ledger_rag_cites_only_governed_sources_and_has_no_financial_authority():
    f=factory()
    with f() as db:
        _,c=setup_case(db,"rag48");intel=RecoverySettlementIntelligenceService(db,"tenant-a");out=intel.copilot("finance-op","Explain the provider recovery target and remaining settlement balance with evidence citations.",provider_organization_id="org-a",settlement_case_id=c.settlement_case_id)
        assert out["citations"] and all(x["citation_id"].startswith(("recovery_settlement:","recovery_position:","settlement_evidence:","ledger_correlation:","completion_certificate:")) for x in out["citations"])
        assert out["authority"]=={"accounting":"none","fund_movement":"none"} and "read-only/recommendation-only" in out["answer"]

def test_release48_worker_migration_and_service_authority_fail_closed():
    root=Path(__file__).resolve().parents[2];domain=(root/'backend/app/domain/recovery_settlement_intelligence.py').read_text();service=(root/'backend/app/services/recovery_settlement_intelligence.py').read_text();worker=(root/'backend/app/workers/recovery_settlement_intelligence.py').read_text();migration=(root/'backend/alembic/versions/0043_recovery_settlement_reconciliation_intelligence.py').read_text()
    for token in ['"ai_can_alter_balances": False','"worker_can_create_bank_transaction": False','"worker_can_collect_funds": False','"automatic_fund_movement": False']:assert token in domain
    for forbidden in ['verify_evidence(', '_post_journal(', 'decide_certificate(', 'authorize_packet(', 'handoff(', 'collect_funds(', 'move_money(']:assert forbidden not in worker
    for forbidden in ['_post_journal(', 'decide_certificate(', 'authorize_packet(', 'collect_funds(', 'move_money(']:assert forbidden not in service
    assert 'down_revision="0042_recovery_settlement_financial_closeout"' in migration and 'FORCE ROW LEVEL SECURITY' in migration and 'reject_recovery_settlement_intelligence_mutation' in migration
