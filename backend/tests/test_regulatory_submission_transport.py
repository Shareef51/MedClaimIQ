from __future__ import annotations
import hashlib,hmac
from pathlib import Path
import pytest
from app.services.regulatory_submission_transport import RegulatorySubmissionTransportService,_canon,_secret
from app.services.review_workbench import ReviewConflictError
from tests.test_recovery_control_assurance import certified_reporting_fixture,factory


def certified_package(db,key):
    control,rp,_,_=certified_reporting_fixture(db,key);p=control.create_package(rp.reporting_period_id,"acct-controller",idempotency_key=f"{key}-pkg");control.lock_package(p.package_id,"acct-controller",expected_source_watermark_sha256=p.source_watermark_sha256);control.certify_package(p.package_id,"auditor-user",rationale="Independent human checker certifies this locked package before any transport release authorization.");return control,rp,p

def destination(svc):return svc.create_destination("auditor-user",destination_key="regulator-a",regulator_name="Synthetic Recovery Regulator",transport_type="sandbox_api",endpoint_reference="secret://regulator-a/api",schema_name="recovery-closeout",schema_version="2026-01",registry_version=1)

def test_one_time_human_release_encrypted_envelope_and_idempotent_worker_dispatch():
    f=factory()
    with f() as db:
        _,_,p=certified_package(db,"p50flow");svc=RegulatorySubmissionTransportService(db,"tenant-a");d=destination(svc)
        rel=svc.release(p.package_id,"auditor-user",destination_id=d.destination_id,schema_name=d.schema_name,schema_version=d.schema_version,release_reason="Human auditor authorizes this exact certified package version for the registered regulator destination.",idempotency_key="p50-release")
        again=svc.release(p.package_id,"auditor-user",destination_id=d.destination_id,schema_name=d.schema_name,schema_version=d.schema_version,release_reason="Idempotent replay of the same one-time human regulatory submission release.",idempotency_key="p50-release")
        assert again.release_id==rel.release_id
        tx=svc.repo.transmission_for_release(rel.release_id);assert tx.status=="queued" and p.locked_manifest_sha256 not in tx.encrypted_envelope and len(tx.envelope_signature)==64
        sent=svc.lease_and_dispatch("worker-1");assert sent.status=="sent" and sent.attempt_count==1 and sent.external_submission_reference
        assert svc.lease_and_dispatch("worker-2") is None

def test_schema_version_mismatch_and_uncertified_package_fail_closed():
    f=factory()
    with f() as db:
        control,rp,_,_=certified_reporting_fixture(db,"p50schema");p=control.create_package(rp.reporting_period_id,"acct-controller",idempotency_key="p50schema-pkg")
        svc=RegulatorySubmissionTransportService(db,"tenant-a");d=destination(svc)
        with pytest.raises(ReviewConflictError,match="certification"):svc.release(p.package_id,"auditor-user",destination_id=d.destination_id,schema_name=d.schema_name,schema_version=d.schema_version,release_reason="Human release cannot bypass required Release 49 maker checker certification.",idempotency_key="bad-cert")
        control.lock_package(p.package_id,"acct-controller",expected_source_watermark_sha256=p.source_watermark_sha256);control.certify_package(p.package_id,"auditor-user",rationale="Independent audit checker certifies the locked package before transport testing.")
        with pytest.raises(ReviewConflictError,match="schema/version"):svc.release(p.package_id,"auditor-user",destination_id=d.destination_id,schema_name=d.schema_name,schema_version="wrong",release_reason="Human release must fail when the registered destination schema does not match.",idempotency_key="bad-schema")

def test_signed_acknowledgment_acceptance_rejection_idempotency_and_traceability():
    f=factory()
    with f() as db:
        _,_,p=certified_package(db,"p50ack");svc=RegulatorySubmissionTransportService(db,"tenant-a");d=destination(svc);rel=svc.release(p.package_id,"auditor-user",destination_id=d.destination_id,schema_name=d.schema_name,schema_version=d.schema_version,release_reason="Human auditor authorizes exact certified package transport for acknowledgment verification.",idempotency_key="p50ack-release");tx=svc.lease_and_dispatch("worker-ack")
        payload={"destination_id":d.destination_id,"external_event_id":"evt-1","external_submission_reference":tx.external_submission_reference,"acknowledgment_status":"accepted","receipt_payload":{"receipt":"ACK-50"},"rejection_code":None,"rejection_reason":None};sig=hmac.new(_secret("REGULATORY_ACK_WEBHOOK_SECRET","medclaimiq-release50-development-ack"),_canon(payload).encode(),hashlib.sha256).hexdigest()
        ack=svc.acknowledgment(signature=sig,**payload);assert ack.signature_verified and svc.repo.transmission(tx.transmission_id).status=="acknowledged"
        same=svc.acknowledgment(signature=sig,**payload);assert same.acknowledgment_id==ack.acknowledgment_id
        trace=svc.traceability(tx.transmission_id,"auditor-user");assert trace["package"]["locked_manifest_sha256"]==p.locked_manifest_sha256 and trace["acknowledgments"][0]["receipt_sha256"]==ack.receipt_sha256 and trace["authority"]["worker_can_authorize_submission_release"] is False

def test_regulator_rejection_creates_incident_and_requires_human_recovery():
    f=factory()
    with f() as db:
        _,_,p=certified_package(db,"p50reject");svc=RegulatorySubmissionTransportService(db,"tenant-a");d=destination(svc);rel=svc.release(p.package_id,"auditor-user",destination_id=d.destination_id,schema_name=d.schema_name,schema_version=d.schema_version,release_reason="Human release for synthetic rejection and recovery workflow verification.",idempotency_key="p50reject-release");tx=svc.lease_and_dispatch("worker-reject")
        payload={"destination_id":d.destination_id,"external_event_id":"evt-reject","external_submission_reference":tx.external_submission_reference,"acknowledgment_status":"rejected","receipt_payload":{"status":"rejected"},"rejection_code":"SCHEMA_RULE_17","rejection_reason":"Synthetic regulator validation rejection."};sig=hmac.new(_secret("REGULATORY_ACK_WEBHOOK_SECRET","medclaimiq-release50-development-ack"),_canon(payload).encode(),hashlib.sha256).hexdigest();svc.acknowledgment(signature=sig,**payload)
        assert svc.repo.transmission(tx.transmission_id).status=="rejected" and any(x.incident_type=="regulator_rejection" for x in svc.repo.incidents())
        recovered=svc.recover(tx.transmission_id,"auditor-user",rationale="Human auditor authorizes transport retry after reviewing the external regulator rejection.");assert recovered.status=="retry_pending"

def test_release50_worker_has_no_authorization_financial_or_fund_movement_calls():
    root=Path(__file__).resolve().parents[2];worker=(root/'backend/app/workers/regulatory_submission_transport.py').read_text();service=(root/'backend/app/services/regulatory_submission_transport.py').read_text();migration=(root/'backend/alembic/versions/0045_regulatory_submission_transport.py').read_text()
    for forbidden in ['release(', 'certify_package(', '_post_journal(', 'authorize_packet(', 'collect_funds(', 'move_money(']:assert forbidden not in worker
    for forbidden in ['_post_journal(', 'authorize_packet(', 'collect_funds(', 'move_money(']:assert forbidden not in service
    assert 'down_revision="0044_recovery_portfolio_control_assurance"' in migration and 'FORCE ROW LEVEL SECURITY' in migration and 'guard_regulatory_submission_releases_immutable' in migration

def test_correction_amendment_resubmission_supersedes_prior_transmission_without_rewriting_it():
    f=factory()
    with f() as db:
        control,rp,p1=certified_package(db,"p50amend");svc=RegulatorySubmissionTransportService(db,"tenant-a");d=destination(svc);r1=svc.release(p1.package_id,"auditor-user",destination_id=d.destination_id,schema_name=d.schema_name,schema_version=d.schema_version,release_reason="Human auditor releases original certified package version one for external submission.",idempotency_key="p50amend-r1");tx1=svc.lease_and_dispatch("worker-amend-1")
        payload={"destination_id":d.destination_id,"external_event_id":"evt-amend-1","external_submission_reference":tx1.external_submission_reference,"acknowledgment_status":"rejected","receipt_payload":{"reason":"validation"},"rejection_code":"R17","rejection_reason":"Regulator requests corrected metadata."};sig=hmac.new(_secret("REGULATORY_ACK_WEBHOOK_SECRET","medclaimiq-release50-development-ack"),_canon(payload).encode(),hashlib.sha256).hexdigest();svc.acknowledgment(signature=sig,**payload)
        assert control.repo.package(p1.package_id).status=="submitted"
        p2=control.create_package(rp.reporting_period_id,"acct-controller",correction_of_package_id=p1.package_id,amendment_reason="Correct regulator-requested metadata while preserving certified accounting and recovery source evidence.",idempotency_key="p50amend-p2");control.lock_package(p2.package_id,"acct-controller",expected_source_watermark_sha256=p2.source_watermark_sha256);control.certify_package(p2.package_id,"auditor-user",rationale="Independent human checker certifies amendment package version two before a new transport release.")
        r2=svc.release(p2.package_id,"auditor-user",destination_id=d.destination_id,schema_name=d.schema_name,schema_version=d.schema_version,release_reason="Human auditor separately releases the certified correction package version for resubmission.",idempotency_key="p50amend-r2");tx2=svc.repo.transmission_for_release(r2.release_id)
        assert tx2.supersedes_transmission_id==tx1.transmission_id and tx2.transmission_id!=tx1.transmission_id and svc.repo.transmission(tx1.transmission_id).status=="rejected"
