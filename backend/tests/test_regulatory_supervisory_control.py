from __future__ import annotations
import hashlib,hmac
from datetime import date,timedelta
from pathlib import Path
import pytest
from app.services.regulatory_submission_transport import RegulatorySubmissionTransportService,_canon,_secret
from app.services.regulatory_supervisory_control import RegulatorySupervisoryControlService
from app.services.review_workbench import ReviewConflictError
from tests.test_recovery_control_assurance import factory
from tests.test_regulatory_submission_transport import certified_package,destination


def ack(svc,d,tx,status="accepted",event="evt-51",code=None,reason=None):
    payload={"destination_id":d.destination_id,"external_event_id":event,"external_submission_reference":tx.external_submission_reference,"acknowledgment_status":status,"receipt_payload":{"release":51,"status":status},"rejection_code":code,"rejection_reason":reason}
    sig=hmac.new(_secret("REGULATORY_ACK_WEBHOOK_SECRET","medclaimiq-release50-development-ack"),_canon(payload).encode(),hashlib.sha256).hexdigest()
    return svc.acknowledgment(signature=sig,**payload)


def accepted_fixture(db,key="p51"):
    control,rp,p=certified_package(db,key);transport=RegulatorySubmissionTransportService(db,"tenant-a");d=destination(transport);rel=transport.release(p.package_id,"auditor-user",destination_id=d.destination_id,schema_name=d.schema_name,schema_version=d.schema_version,release_reason="Human auditor releases the certified package for Release 51 supervisory reconciliation testing.",idempotency_key=f"{key}-release");tx=transport.lease_and_dispatch(f"{key}-worker");ack(transport,d,tx,event=f"{key}-ack");return control,rp,p,transport,d,rel,tx


def test_accepted_submission_tieout_attestation_and_independent_human_supervisory_certification():
    f=factory()
    with f() as db:
        _,_,p,_,_,_,tx=accepted_fixture(db,"p51ok");svc=RegulatorySupervisoryControlService(db,"tenant-a");assert svc.refresh_cases(transmission_id=tx.transmission_id)["created"]==1
        case=svc.repo.case_for_transmission(tx.transmission_id);att=svc.prepare_attestation(case.case_id,"acct-controller",expected_case_version=1)
        assert not att.material_blockers and float(att.control_effectiveness_pct)==100.0 and att.source_watermark_sha256==case.source_snapshot_sha256
        case=svc.repo.case(case.case_id);cert=svc.certify(case.case_id,att.attestation_id,"auditor-user",conclusion="reconciled",rationale="Independent human regulatory supervisor certifies package, release, transport and cryptographically verified regulator acknowledgment tie-outs.",expected_case_version=case.case_version)
        assert cert.supervisor_user_id=="auditor-user" and len(cert.certification_sha256)==64 and svc.repo.case(case.case_id).status=="certified"
        trace=svc.traceability(case.case_id,"auditor-user");assert trace["release49_release50"]["locked_manifest_sha256"]==p.locked_manifest_sha256 and trace["release49_release50"]["acknowledgments"][0]["signature_verified"] is True


def test_outstanding_submission_and_same_human_maker_checker_fail_closed():
    f=factory()
    with f() as db:
        _,_,p=certified_package(db,"p51open");transport=RegulatorySubmissionTransportService(db,"tenant-a");d=destination(transport);rel=transport.release(p.package_id,"auditor-user",destination_id=d.destination_id,schema_name=d.schema_name,schema_version=d.schema_version,release_reason="Human auditor releases package but no acknowledgment is supplied to prove blocking supervision.",idempotency_key="p51open-release");tx=transport.lease_and_dispatch("p51open-worker")
        svc=RegulatorySupervisoryControlService(db,"tenant-a");svc.refresh_cases(transmission_id=tx.transmission_id);case=svc.repo.case_for_transmission(tx.transmission_id);att=svc.prepare_attestation(case.case_id,"auditor-user",expected_case_version=1)
        assert {x["control_code"] for x in att.material_blockers}>={"cryptographic_acknowledgment","accepted_or_effective_amendment"}
        with pytest.raises(ReviewConflictError,match="maker and supervisory checker"):svc.certify(case.case_id,att.attestation_id,"auditor-user",conclusion="reconciled",rationale="Same human may not certify their own supervisory control attestation.",expected_case_version=svc.repo.case(case.case_id).case_version)


def test_rejection_root_cause_and_effective_amendment_enable_governed_supervisory_reconciliation():
    f=factory()
    with f() as db:
        control,rp,p1=certified_package(db,"p51reject");transport=RegulatorySubmissionTransportService(db,"tenant-a");d=destination(transport);r1=transport.release(p1.package_id,"auditor-user",destination_id=d.destination_id,schema_name=d.schema_name,schema_version=d.schema_version,release_reason="Human release for rejected regulatory submission supervisory workflow.",idempotency_key="p51reject-r1");tx1=transport.lease_and_dispatch("p51reject-w1");ack(transport,d,tx1,status="rejected",event="p51reject-e1",code="RULE-51",reason="Synthetic regulator rule validation rejection")
        p2=control.create_package(rp.reporting_period_id,"acct-controller",correction_of_package_id=p1.package_id,amendment_reason="Correct regulator-requested metadata while preserving certified recovery and accounting source evidence.",idempotency_key="p51reject-p2");control.lock_package(p2.package_id,"acct-controller",expected_source_watermark_sha256=p2.source_watermark_sha256);control.certify_package(p2.package_id,"auditor-user",rationale="Independent checker certifies amendment package before separate human transport release.")
        r2=transport.release(p2.package_id,"auditor-user",destination_id=d.destination_id,schema_name=d.schema_name,schema_version=d.schema_version,release_reason="Human auditor releases certified correction package after regulator rejection.",idempotency_key="p51reject-r2");tx2=transport.lease_and_dispatch("p51reject-w2");ack(transport,d,tx2,status="accepted",event="p51reject-e2")
        svc=RegulatorySupervisoryControlService(db,"tenant-a");svc.refresh_cases(transmission_id=tx1.transmission_id);case=svc.repo.case_for_transmission(tx1.transmission_id)
        svc.classify_rejection(case.case_id,"acct-controller",root_cause="schema_validation",rationale="Human reviewer classifies the regulator rejection using the signed rejection receipt and package schema evidence.",expected_case_version=case.case_version);case=svc.repo.case(case.case_id)
        svc.record_amendment_effectiveness(case.case_id,"acct-controller",effectiveness="effective",rationale="Superseding certified amendment has a cryptographically verified accepted regulator acknowledgment.",expected_case_version=case.case_version);case=svc.repo.case(case.case_id)
        att=svc.prepare_attestation(case.case_id,"acct-controller",expected_case_version=case.case_version);assert not att.material_blockers
        case=svc.repo.case(case.case_id);cert=svc.certify(case.case_id,att.attestation_id,"auditor-user",conclusion="reconciled_after_amendment",rationale="Independent supervisor certifies rejection root cause, amendment lineage and accepted corrected submission acknowledgment.",expected_case_version=case.case_version);assert cert.conclusion=="reconciled_after_amendment"


def test_correspondence_calendar_audit_export_and_sla_operations_are_provenance_only():
    f=factory()
    with f() as db:
        _,_,_,_,d,_,tx=accepted_fixture(db,"p51ops");svc=RegulatorySupervisoryControlService(db,"tenant-a");svc.refresh_cases(transmission_id=tx.transmission_id);case=svc.repo.case_for_transmission(tx.transmission_id)
        corr=svc.correspondence(case.case_id,"acct-controller",direction="outbound",channel="regulator_portal",subject="Supervisory reconciliation inquiry",body="Human supervisor requests clarification for the acknowledged filing control record.",external_reference="REG-CORR-51",idempotency_key="p51-corr")
        deadline=svc.create_deadline("acct-controller",destination_id=d.destination_id,deadline_key="annual-recovery-control-2027",due_date=date.today()+timedelta(days=30),description="Synthetic portfolio regulatory reporting deadline used for operations planning.")
        ann=svc.annotate(case.case_id,"auditor-user",annotation_type="control_review",body="Acknowledgment receipt and package manifest tie out to the same certified submission version.",source_refs=[{"transmission_id":tx.transmission_id}],idempotency_key="p51-ann")
        export=svc.audit_export(case.case_id,"auditor-user");assert len(export["manifest_sha256"])==64 and export["financial_mutation_authority"] is False and corr.payload_sha256 and deadline.status=="open" and ann.body_sha256


def test_worker_and_service_have_no_submission_financial_accounting_or_fund_authority_and_migration_is_rls_immutable():
    root=Path(__file__).resolve().parents[2];worker=(root/'backend/app/workers/regulatory_supervisory_control.py').read_text();service=(root/'backend/app/services/regulatory_supervisory_control.py').read_text();migration=(root/'backend/alembic/versions/0046_regulatory_supervisory_control.py').read_text()
    for forbidden in ['certify(', 'release(', 'lease_and_dispatch(', '_post_journal(', 'authorize_packet(', 'collect_funds(', 'move_money(']:assert forbidden not in worker
    for forbidden in ['_post_journal(', 'authorize_packet(', 'collect_funds(', 'move_money(']:assert forbidden not in service
    assert 'down_revision="0045_regulatory_submission_transport"' in migration and 'FORCE ROW LEVEL SECURITY' in migration and 'guard_regulatory_supervisory_certifications_immutable' in migration
