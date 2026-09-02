from __future__ import annotations

import hashlib
import hmac
import json
import zipfile
from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path

import pytest
from sqlalchemy import select

from app.domain.communication_delivery import DispatchStatus
from app.models.communication_delivery import CommunicationEndpointModel, CommunicationTemplateModel
from app.models.post_decision import DecisionNoticeModel
from app.services.communication_delivery import CommunicationDeliveryService
from app.services.post_decision import PostDecisionService
from app.services.review_workbench import ReviewConflictError
from app.core.config import get_settings
from test_post_decision_communications_appeals import factory, close_original


def setup_released_notice(db, *, destination="patient@example.test", locale="en"):
    close_original(db)
    delivery=CommunicationDeliveryService(db,"tenant-a")
    templates=delivery.provision_baseline_templates("reviewer-1","reviewer-2")
    assert len(templates)==9 and all(x.status=="approved" for x in templates)
    endpoint=delivery.upsert_endpoint("claim-1","patient-user",audience="patient",channel="email",destination=destination,consent_status="opted_in",locale=locale,accessibility_preferences={"large_text":True,"plain_text":True})
    notice=PostDecisionService(db,"tenant-a").repo.notices("claim-1")[0]
    PostDecisionService(db,"tenant-a").release_notice("claim-1",notice.notice_id,"reviewer-1",idempotency_key="release37-release")
    db.flush()
    return delivery, notice, endpoint


def test_destinations_are_encrypted_and_template_approval_is_dual_control():
    f=factory()
    with f() as db:
        close_original(db); svc=CommunicationDeliveryService(db,"tenant-a")
        with pytest.raises(ReviewConflictError,match="two different"):
            svc.provision_baseline_templates("reviewer-1","reviewer-1")
        svc.provision_baseline_templates("reviewer-1","reviewer-2")
        endpoint=svc.upsert_endpoint("claim-1","patient-user",audience="patient",channel="email",destination="secret.patient@example.test",consent_status="opted_in",locale="en",accessibility_preferences={"semantic_html":True})
        assert "secret.patient@example.test" not in endpoint.destination_ciphertext
        assert svc.cipher.decrypt(endpoint.destination_ciphertext)=="secret.patient@example.test"
        view=svc.endpoint_view(endpoint)
        assert "destination_ciphertext" not in view and "destination" not in view
        approved=list(db.scalars(select(CommunicationTemplateModel).where(CommunicationTemplateModel.status=="approved")))
        assert approved and all(x.approved_by_user_id and x.approved_by_user_id!=x.created_by_user_id for x in approved)


def test_human_release_auto_queues_portal_and_email_then_worker_lease_dispatches():
    f=factory()
    with f() as db:
        svc,notice,_=setup_released_notice(db)
        rows=svc.repo.dispatches(notice_id=notice.notice_id)
        assert {x.channel for x in rows}=={"portal","email"}
        assert all(x.status=="queued" for x in rows)
        leased=svc.lease("worker-a",limit=10)
        assert len(leased)==2 and all(x.lease_owner=="worker-a" for x in leased)
        portal=next(x for x in leased if x.channel=="portal"); email=next(x for x in leased if x.channel=="email")
        assert svc.execute(portal.dispatch_id,"worker-a")["status"]=="delivered"
        email_result=svc.execute(email.dispatch_id,"worker-a")
        assert email_result["status"]=="sent" and email_result["provider_message_id"]
        assert notice.released_by_user_id=="reviewer-1"  # transport never manufactures release authority


def test_signed_webhook_receipt_is_idempotent_and_reconciliation_marks_delivery():
    f=factory()
    with f() as db:
        svc,notice,_=setup_released_notice(db)
        leased=svc.lease("worker-a",limit=10)
        email=next(x for x in leased if x.channel=="email")
        svc.execute(email.dispatch_id,"worker-a")
        payload={"tenant_id":"tenant-a","dispatch_id":email.dispatch_id,"provider_event_id":"evt-001","provider_message_id":email.provider_message_id,"status":"delivered","occurred_at":datetime.now(UTC).isoformat()}
        raw=json.dumps(payload,separators=(",",":")).encode()
        secret=get_settings().communication_provider_webhook_secret.get_secret_value().encode()
        signature=hmac.new(secret,raw,hashlib.sha256).hexdigest()
        assert svc.verify_webhook_signature(raw,signature)
        receipt=svc.record_receipt(email.provider_name,payload,signature_verified=True)
        duplicate=svc.record_receipt(email.provider_name,payload,signature_verified=True)
        assert receipt.receipt_id==duplicate.receipt_id
        recon=svc.reconcile_notice(notice.notice_id,idempotency_key="reconcile-1")
        assert recon.status=="reconciled" and recon.delivered_dispatches>=1
        assert db.get(DecisionNoticeModel,notice.notice_id).status=="delivered"


def test_retry_backoff_dead_letter_and_human_incident_recovery():
    f=factory()
    with f() as db:
        svc,notice,_=setup_released_notice(db,destination="fail:patient@example.test")
        email=next(x for x in svc.lease("worker-fail",limit=10) if x.channel=="email")
        previous=None
        for attempt in range(1,get_settings().communication_max_delivery_attempts+1):
            result=svc.execute(email.dispatch_id,"worker-fail")
            email=svc.repo.dispatch(email.dispatch_id)
            assert email.attempt_count==attempt
            if attempt<get_settings().communication_max_delivery_attempts:
                assert result["status"]==DispatchStatus.RETRY_PENDING.value
                if previous is not None: assert email.next_attempt_at>=previous
                previous=email.next_attempt_at
                email.next_attempt_at=datetime.now(UTC)-timedelta(seconds=1); db.flush()
                leased=svc.lease("worker-fail",limit=10)
                email=next(x for x in leased if x.dispatch_id==email.dispatch_id)
            else:
                assert result["status"]==DispatchStatus.DEAD_LETTERED.value
        recovered=svc.recover_dispatch(email.dispatch_id,"reviewer-2","Provider incident cleared; authorized human operations reviewer approved transport retry.")
        assert recovered.status==DispatchStatus.RETRY_PENDING.value
        assert svc.repo.incidents(status="open")==[]


def test_pdf_audit_export_retention_legal_hold_and_no_destination_leak():
    f=factory()
    with f() as db:
        svc,notice,_=setup_released_notice(db,destination="patient.private@example.test")
        portal=next(x for x in svc.lease("worker-a",limit=10) if x.channel=="portal")
        svc.execute(portal.dispatch_id,"worker-a"); svc.reconcile_notice(notice.notice_id,idempotency_key="reconcile-pdf")
        pdf=svc.render_notice_pdf(notice.notice_id,"en")
        assert pdf.startswith(b"%PDF") and len(pdf)>500
        before=svc.retention_status("claim-1"); assert before["destructive_purge_automatic"] is False
        hold=svc.place_legal_hold("claim-1","reviewer-2","Regulatory audit and appeal preservation requires retention beyond ordinary disposition.")
        during=svc.retention_status("claim-1"); assert during["legal_hold"] and during["disposition_blocked"]
        svc.release_legal_hold(hold.hold_id,"reviewer-3","Regulatory preservation requirement has ended after documented audit completion.")
        assert not svc.retention_status("claim-1")["legal_hold"]
        archive,digest=svc.build_audit_export("claim-1")
        assert hashlib.sha256(archive).hexdigest()==digest
        assert b"patient.private@example.test" not in archive
        with zipfile.ZipFile(BytesIO(archive)) as zf:
            assert "manifest.json" in zf.namelist() and any(x.endswith(".pdf") for x in zf.namelist())
            manifest=json.loads(zf.read("manifest.json")); assert manifest["manifest_sha256"] and manifest["manifest_hmac_sha256"]


def test_delivery_dashboard_and_traceability_do_not_grant_adjudication_authority():
    f=factory()
    with f() as db:
        svc,notice,_=setup_released_notice(db)
        portal=next(x for x in svc.lease("worker-a",limit=10) if x.channel=="portal"); svc.execute(portal.dispatch_id,"worker-a")
        dashboard=svc.dashboard(); trace=svc.traceability("claim-1")
        assert dashboard["adjudication_authority"]=="none"
        assert trace["provider_and_worker_adjudication_authority"] is False
        assert any(x["relationship"]=="human_released_notice_dispatched" for x in trace["edges"])


def test_release37_migration_and_authority_source_contracts():
    migration=Path("alembic/versions/0032_communication_delivery_compliance.py").read_text()
    assert 'down_revision="0031_post_decision_communications_appeals"' in migration
    assert "FORCE ROW LEVEL SECURITY" in migration
    assert "communication_receipts_immutable" in migration
    assert "communication_reconciliations_immutable" in migration
    assert "communication_templates_approved_immutable" in migration
    service=Path("app/services/communication_delivery.py").read_text()
    providers=Path("app/communications/providers.py").read_text()
    forbidden=("resolve_appeal(","GovernedClosureService(","HumanDecision.","record_human_decision")
    assert not any(token in service or token in providers for token in forbidden)
    assert "human-released" in service


def test_webhook_public_prefix_and_frontend_operations_source_contract():
    from app.middleware.authentication import AuthenticationMiddleware
    middleware=AuthenticationMiddleware.__new__(AuthenticationMiddleware)
    middleware.public_paths=frozenset({"/api/v1/communications/webhooks/*"})
    assert middleware._is_public("/api/v1/communications/webhooks/email-sandbox")
    assert not middleware._is_public("/api/v1/claims/claim-1")
    main=Path("app/main.py").read_text(); api=Path("app/api/v1/communication_delivery.py").read_text()
    frontend=Path("../frontend/app/review/communications/page.tsx").read_text(); client=Path("../frontend/lib/api.ts").read_text()
    assert 'communications/webhooks/*' in main
    assert '/communications/webhooks/{provider_name}' in api
    assert "Delivery, compliance & reconciliation" in frontend
    assert "communicationDashboard" in client and "reconcileNoticeDelivery" in client


def test_release37_production_worker_and_secret_wiring_contract():
    values=Path("../infra/helm/medclaimiq/values.yaml").read_text()
    workers=Path("../infra/helm/medclaimiq/templates/workers.yaml").read_text()
    secrets=Path("../infra/helm/medclaimiq/templates/secretproviderclass.yaml").read_text()
    runtime=Path("app/workers/production_runtime.py").read_text()
    assert "communication-delivery" in values and "communication-delivery" in runtime
    for token in ("COMMUNICATION_DESTINATION_ENCRYPTION_SECRET","COMMUNICATION_PROVIDER_WEBHOOK_SECRET","COMMUNICATION_WORKER_TOKEN"):
        assert token in workers and token in secrets
