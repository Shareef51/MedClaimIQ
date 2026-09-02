from __future__ import annotations
from datetime import UTC,datetime
from decimal import Decimal
from pathlib import Path
import pytest
from app.models.tenancy import UserAccountModel,TenantMembershipModel
from app.models.communication_delivery import CommunicationLegalHoldModel
from app.services.accounting_ledger import AccountingLedgerService
from app.services.recovery_settlement import RecoverySettlementService
from app.services.recovery_settlement_intelligence import RecoverySettlementIntelligenceService
from app.services.recovery_control_assurance import RecoveryControlAssuranceService
from app.services.review_workbench import ReviewConflictError
from tests.test_recovery_settlement import factory,release46_final,settlement_journal


def add_control_users(db):
    for uid,role,mid in (("acct-controller","accounting_controller","m-p49-controller"),("auditor-user","auditor","m-p49-auditor")):
        if db.get(UserAccountModel,uid) is None:
            db.add(UserAccountModel(user_id=uid,external_issuer="https://id.example",external_subject=uid,display_name=uid,status="active"));db.flush();db.add(TenantMembershipModel(membership_id=mid,tenant_id="tenant-a",user_id=uid,role=role,status="active"))
    db.flush()


def certified_reporting_fixture(db,key="p49",with_hold=False):
    _,recovery,_,_=release46_final(db,key,Decimal("100"));rs=RecoverySettlementService(db,"tenant-a");case=rs.create_from_recovery(recovery.recovery_case_id,"finance-op",idempotency_key=f"{key}-case")
    evidence=rs.submit_evidence(case.settlement_case_id,"provider-user",evidence_type="bank_repayment",amount=Decimal("100"),currency="USD",installment_sequence=1,external_reference=f"{key}-BANK",bank_reference=f"{key}-BANK",remittance_reference=None,provider_reference="org-a",evidence_refs=[],occurred_at=None,idempotency_key=f"{key}-e")
    rs.verify_evidence(case.settlement_case_id,evidence.settlement_evidence_id,"finance-op",reference_match=True,verification_rationale="Human finance operator verifies the external provider repayment reference for control-assurance reporting.",expected_case_version=2,idempotency_key=f"{key}-v")
    journal=settlement_journal(db,Decimal("100"),f"{key}-journal");rs.correlate_ledger(case.settlement_case_id,evidence.settlement_evidence_id,"finance-op",journal_id=journal.journal_id,amount=Decimal("100"),currency="USD",idempotency_key=f"{key}-corr")
    current=rs.repo.case(case.settlement_case_id);cert=rs.prepare_certificate(case.settlement_case_id,"finance-op",accounting_period_id=journal.period_id,reason_codes=["external_repayment_verified","ledger_reconciled"],rationale="Human finance operator prepares the exact recovery financial closeout after repayment and ledger correlation.",expected_case_version=current.case_version,idempotency_key=f"{key}-cert")
    current=rs.repo.case(case.settlement_case_id);rs.decide_certificate(case.settlement_case_id,cert.certificate_id,"finance-approver-2",action="approve",rationale="Independent finance approver certifies exact recovery closeout before regulatory control assurance.",expected_case_version=current.case_version,idempotency_key=f"{key}-approve")
    add_control_users(db)
    if with_hold:
        db.add(CommunicationLegalHoldModel(hold_id=f"hold-{key}",tenant_id="tenant-a",claim_id="claim-1",reason="Preserve certified recovery reporting evidence for audit review.",placed_by_user_id="auditor-user",placed_at=datetime.now(UTC),released_by_user_id=None,released_at=None,release_reason=None));db.flush()
    period=AccountingLedgerService(db,"tenant-a").repo.period(journal.period_id);period.status="closed";period.close_summary={"journal_count":1,"total_debits":"100.00","total_credits":"100.00","fixture":"represents prior governed Release 41 human close"};period.close_sha256="c"*64;period.closed_by_user_id="acct-controller";period.closed_at=datetime.now(UTC);period.lock_version=2;db.flush()
    intel=RecoverySettlementIntelligenceService(db,"tenant-a");statement=intel.provider_statement("org-a","finance-op");intel.publish_statement(statement["statement_id"],"finance-approver",idempotency_key=f"{key}-statement-publish");intel.accounting_closeout_report(period.period_id,"finance-op",persist=True)
    svc=RecoveryControlAssuranceService(db,"tenant-a");rp=svc.create_reporting_period("acct-controller",period_key=f"{key}-2026-08",report_type="recovery_accounting_closeout",jurisdiction="internal-control-reporting",start_date=period.start_date,end_date=period.end_date,accounting_period_ids=[period.period_id],idempotency_key=f"{key}-reporting-period")
    return svc,rp,period,case


def test_portfolio_attestation_tieout_statement_completeness_and_legal_hold_retention_manifest():
    f=factory()
    with f() as db:
        svc,rp,_,case=certified_reporting_fixture(db,"attest49",with_hold=True);before=(case.target_amount,case.verified_amount,case.remaining_amount,case.case_version)
        att=svc.prepare_attestation(rp.reporting_period_id,"acct-controller");assert not att.material_blockers and float(att.control_effectiveness_pct)==100.0 and len(att.payload_sha256)==64
        p=svc.create_package(rp.reporting_period_id,"acct-controller",idempotency_key="p49-package-hold");assert p.manifest["retention_and_legal_hold"]["active_legal_hold_count"]==1 and p.manifest["retention_and_legal_hold"]["destructive_purge_automatic"] is False
        assert svc.repo.samples(p.package_id) and (case.target_amount,case.verified_amount,case.remaining_amount,case.case_version)==before


def test_material_control_exception_blocks_lock_before_human_certification():
    f=factory()
    with f() as db:
        _,recovery,_,_=release46_final(db,"blocked49",Decimal("100"));rs=RecoverySettlementService(db,"tenant-a");case=rs.create_from_recovery(recovery.recovery_case_id,"finance-op",idempotency_key="blocked49-case");journal=settlement_journal(db,Decimal("100"),"blocked49-journal");add_control_users(db)
        svc=RecoveryControlAssuranceService(db,"tenant-a");rp=svc.create_reporting_period("acct-controller",period_key="blocked49-period",report_type="recovery_accounting_closeout",jurisdiction="internal-control-reporting",start_date=datetime.now(UTC).date(),end_date=datetime.now(UTC).date(),accounting_period_ids=[journal.period_id],idempotency_key="blocked49-rp")
        p=svc.create_package(rp.reporting_period_id,"acct-controller",idempotency_key="blocked49-pkg");codes={x["control_code"] for x in p.material_blockers};assert "accounting_periods_closed" in codes and "release48_closeout_report_completeness" in codes
        with pytest.raises(ReviewConflictError,match="material control exceptions"):svc.lock_package(p.package_id,"acct-controller",expected_source_watermark_sha256=p.source_watermark_sha256)
        assert case.status=="awaiting_settlement_evidence"


def test_hash_lock_maker_checker_human_staging_receipt_and_immutable_certification_chain():
    f=factory()
    with f() as db:
        svc,rp,_,_=certified_reporting_fixture(db,"flow49");p=svc.create_package(rp.reporting_period_id,"acct-controller",idempotency_key="flow49-pkg");p=svc.lock_package(p.package_id,"acct-controller",expected_source_watermark_sha256=p.source_watermark_sha256);assert p.status=="locked" and len(p.locked_manifest_sha256)==64
        with pytest.raises(ReviewConflictError,match="maker and checker"):svc.certify_package(p.package_id,"acct-controller",rationale="The package maker cannot self-certify this locked regulatory control package under maker-checker segregation.")
        cert=svc.certify_package(p.package_id,"auditor-user",rationale="Independent human audit checker certifies deterministic tie-outs, provider statement completeness and the locked source watermark.");assert cert.checker_user_id=="auditor-user" and len(cert.certification_sha256)==64
        staged=svc.stage_submission(p.package_id,"auditor-user",rationale="Authorized human auditor stages the certified package for external submission; no background worker submits it.");assert staged.status=="staged"
        receipt=svc.record_submission_receipt(p.package_id,"auditor-user",external_submission_id="REG-EXT-49-1",submission_status="accepted",external_receipt_reference="RECEIPT-49-1",receipt_metadata={"channel":"regulator_portal","recorded_from":"external_receipt"},idempotency_key="flow49-receipt");assert receipt.submission_status=="accepted" and svc.repo.package(p.package_id).status=="submitted"
        trace=svc.traceability(p.package_id,"auditor-user");assert trace["submission_receipt"]["external_submission_id"]=="REG-EXT-49-1" and trace["authority"]=={"ai_certifies":False,"automation_submits":False,"financial_records_mutated":False,"fund_movement":False}


def test_correction_amendment_creates_new_locked_version_and_chains_certification_without_rewriting_original():
    f=factory()
    with f() as db:
        svc,rp,_,_=certified_reporting_fixture(db,"amend49");p1=svc.create_package(rp.reporting_period_id,"acct-controller",idempotency_key="amend49-v1");svc.lock_package(p1.package_id,"acct-controller",expected_source_watermark_sha256=p1.source_watermark_sha256);c1=svc.certify_package(p1.package_id,"auditor-user",rationale="Independent audit checker certifies the original locked control package before the first human-staged submission.");svc.stage_submission(p1.package_id,"auditor-user",rationale="Human auditor stages the first certified regulatory package for external submission.");svc.record_submission_receipt(p1.package_id,"auditor-user",external_submission_id="REG-AMEND-1",submission_status="accepted",external_receipt_reference="REC-AMEND-1",receipt_metadata={},idempotency_key="amend49-r1")
        p2=svc.create_package(rp.reporting_period_id,"acct-controller",correction_of_package_id=p1.package_id,amendment_reason="Correct the externally reported package metadata while preserving the identical certified recovery and ledger source records.",idempotency_key="amend49-v2");assert p2.package_version==2 and p2.correction_of_package_id==p1.package_id and svc.repo.package(p1.package_id).status=="submitted"
        svc.lock_package(p2.package_id,"acct-controller",expected_source_watermark_sha256=p2.source_watermark_sha256);c2=svc.certify_package(p2.package_id,"auditor-user",rationale="Independent audit checker certifies amendment version two without rewriting the original submitted package.");assert c2.previous_certification_sha256==c1.certification_sha256 and c2.certification_sequence==2


def test_audit_annotations_and_hash_chain_are_immutable_derived_provenance():
    f=factory()
    with f() as db:
        svc,rp,_,_=certified_reporting_fixture(db,"audit49");p=svc.create_package(rp.reporting_period_id,"acct-controller",idempotency_key="audit49-pkg");a=svc.add_annotation(p.package_id,"auditor-user",annotation_type="control_evidence_review",body="Audit reviewer sampled the certificate, ledger correlation and provider statement evidence and found the deterministic tie-out internally consistent.",source_refs=[x.source_id for x in svc.repo.samples(p.package_id)[:3]],idempotency_key="audit49-ann");assert len(a.body_sha256)==64
        chain=svc.repo.audit(rp.reporting_period_id);assert len(chain)>=3 and all(chain[i].previous_event_sha256==chain[i-1].event_sha256 for i in range(1,len(chain)))


def test_release49_worker_and_service_have_no_financial_or_regulatory_authority_bypass():
    root=Path(__file__).resolve().parents[2];domain=(root/'backend/app/domain/recovery_control_assurance.py').read_text();worker=(root/'backend/app/workers/recovery_control_assurance.py').read_text();service=(root/'backend/app/services/recovery_control_assurance.py').read_text();migration=(root/'backend/alembic/versions/0044_recovery_portfolio_control_assurance.py').read_text()
    for token in ['"ai_can_certify_regulatory_report": False','"worker_can_record_external_submission_receipt": False','"automatic_regulatory_submission": False','"automatic_fund_movement": False']:assert token in domain
    for forbidden in ['certify_package(', 'stage_submission(', 'record_submission_receipt(', '_post_journal(', 'authorize_packet(', 'handoff(', 'collect_funds(', 'move_money(', 'verify_evidence(']:assert forbidden not in worker
    for forbidden in ['_post_journal(', 'authorize_packet(', 'handoff(', 'collect_funds(', 'move_money(', 'decide_certificate(', 'verify_evidence(']:assert forbidden not in service
    assert 'down_revision="0043_recovery_settlement_reconciliation_intelligence"' in migration and 'FORCE ROW LEVEL SECURITY' in migration and 'guard_regulatory_package_locked_fields' in migration
