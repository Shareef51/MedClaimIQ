from __future__ import annotations

import hashlib
import hmac
import io
import json
import zipfile
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from opentelemetry import trace
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.communications.crypto import DestinationCipher
from app.communications.providers import ProviderRegistry
from app.communications.rendering import render_deterministic, render_pdf_bytes, stable_json_bytes
from app.core.config import get_settings
from app.domain.communication_delivery import CommunicationChannel, ConsentStatus, DispatchStatus, ReceiptStatus, SUPPORTED_LOCALES, TemplateStatus
from app.domain.post_decision import DecisionNoticeStatus
from app.domain.realtime import EventEnvelope, EventTopic
from app.models.communication_delivery import (
    CommunicationDispatchModel, CommunicationEndpointModel, CommunicationIncidentModel,
    CommunicationLegalHoldModel, CommunicationReceiptModel, CommunicationReconciliationModel,
    CommunicationTemplateModel,
)
from app.models.governed_closure import DecisionNotificationIntentModel
from app.models.post_decision import CommunicationDeadLetterModel, DecisionNoticeModel, ExternalCorrespondenceModel
from app.repositories.communication_delivery import CommunicationDeliveryRepository
from app.repositories.post_decision import PostDecisionRepository
from app.repositories.tenancy import MembershipRepository
from app.realtime.events import enqueue_realtime_event
from app.services.review_workbench import ReviewConflictError


def _now() -> datetime: return datetime.now(UTC)
def _utc(value:datetime)->datetime: return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
def _sha(value:object)->str: return hashlib.sha256(stable_json_bytes(value) if not isinstance(value,(bytes,bytearray)) else bytes(value)).hexdigest()
def _canonical(value:object)->bytes: return stable_json_bytes(value)


class CommunicationDeliveryService:
    """Transport, compliance and reconciliation layer for human-released notices only."""

    def __init__(self, session:Session, tenant_id:str, *, providers:ProviderRegistry|None=None):
        self.session=session; self.tenant_id=tenant_id; self.repo=CommunicationDeliveryRepository(session,tenant_id); self.post=PostDecisionRepository(session,tenant_id)
        self.settings=get_settings(); self.providers=providers or ProviderRegistry()
        self.cipher=DestinationCipher(self.settings.communication_destination_encryption_secret.get_secret_value(),key_version=self.settings.communication_destination_key_version)
        self.tracer=trace.get_tracer("medclaimiq.communication-delivery")

    def _require_reviewer(self,user_id:str)->None:
        membership=MembershipRepository(self.session,self.tenant_id).get_by_user(user_id)
        if membership is None or membership.status!="active" or membership.role!="claims_reviewer": raise ReviewConflictError("active human claims reviewer membership required")

    def _emit(self,claim_id:str,event_type:str,aggregate_type:str,aggregate_id:str,metadata:dict,trace_id:str|None=None):
        safe={k:v for k,v in metadata.items() if k in {"status","dispatch_id","notice_id","channel","provider","deadline_status","incident_id"}}
        return enqueue_realtime_event(self.session,envelope=EventEnvelope(event_id=f"cde_{uuid4().hex}",event_type=event_type,tenant_id=self.tenant_id,claim_id=claim_id,aggregate_type=aggregate_type,aggregate_id=aggregate_id,occurred_at=_now(),trace_id=trace_id,producer="medclaimiq-communication-delivery",payload=metadata,metadata=safe),topic=EventTopic.CLAIMS.value)

    def _incident(self,*,claim_id:str|None,dispatch_id:str|None,severity:str,category:str,summary:str)->CommunicationIncidentModel:
        row=self.repo.add(CommunicationIncidentModel(incident_id=f"ci_{uuid4().hex}",tenant_id=self.tenant_id,claim_id=claim_id,dispatch_id=dispatch_id,severity=severity,category=category,status="open",summary=summary,recovery_action=None,created_at=_now(),recovered_at=None))
        if claim_id:self._emit(claim_id,"communication.incident.opened","communication_incident",row.incident_id,{"status":"open","incident_id":row.incident_id,"dispatch_id":dispatch_id})
        return row

    def upsert_endpoint(self,claim_id:str,actor_id:str,*,audience:str,channel:str,destination:str,consent_status:str,locale:str,accessibility_preferences:dict)->CommunicationEndpointModel:
        if locale not in SUPPORTED_LOCALES: raise ReviewConflictError("unsupported communication locale")
        if channel not in {x.value for x in CommunicationChannel}: raise ReviewConflictError("unsupported communication channel")
        existing=self.session.scalar(select(CommunicationEndpointModel).where(CommunicationEndpointModel.tenant_id==self.tenant_id,CommunicationEndpointModel.claim_id==claim_id,CommunicationEndpointModel.audience==audience,CommunicationEndpointModel.channel==channel))
        now=_now(); ciphertext=self.cipher.encrypt(destination); fingerprint=self.cipher.fingerprint(destination)
        if existing:
            existing.destination_ciphertext=ciphertext; existing.destination_fingerprint=fingerprint; existing.encryption_key_version=self.cipher.key_version; existing.consent_status=consent_status; existing.locale=locale; existing.accessibility_preferences=accessibility_preferences; existing.endpoint_version+=1; existing.updated_by_actor_type="authorized_participant_or_reviewer"; existing.updated_by_actor_id=actor_id; existing.updated_at=now; existing.active=True; self.session.flush(); return existing
        return self.repo.add(CommunicationEndpointModel(endpoint_id=f"cep_{uuid4().hex}",tenant_id=self.tenant_id,claim_id=claim_id,audience=audience,channel=channel,destination_ciphertext=ciphertext,destination_fingerprint=fingerprint,encryption_key_version=self.cipher.key_version,consent_status=consent_status,locale=locale,accessibility_preferences=accessibility_preferences,endpoint_version=1,active=True,updated_by_actor_type="authorized_participant_or_reviewer",updated_by_actor_id=actor_id,created_at=now,updated_at=now))

    def endpoint_view(self,row:CommunicationEndpointModel)->dict:
        return {"endpoint_id":row.endpoint_id,"claim_id":row.claim_id,"audience":row.audience,"channel":row.channel,"destination_fingerprint":row.destination_fingerprint,"encrypted_at_rest":True,"encryption_key_version":row.encryption_key_version,"consent_status":row.consent_status,"locale":row.locale,"accessibility_preferences":row.accessibility_preferences,"endpoint_version":row.endpoint_version,"active":row.active}

    def create_template(self,user_id:str,*,template_key:str,template_version:str,locale:str,channel:str,subject_template:str|None,body_template:str,accessibility_schema:dict,change_reason:str)->CommunicationTemplateModel:
        self._require_reviewer(user_id)
        if locale not in SUPPORTED_LOCALES: raise ReviewConflictError("unsupported template locale")
        content={"subject_template":subject_template,"body_template":body_template,"accessibility_schema":accessibility_schema}
        row=CommunicationTemplateModel(template_id=f"ct_{uuid4().hex}",tenant_id=self.tenant_id,template_key=template_key,template_version=template_version,locale=locale,channel=channel,status=TemplateStatus.DRAFT.value,subject_template=subject_template,body_template=body_template,accessibility_schema=accessibility_schema,content_sha256=_sha(content),change_reason=change_reason,created_by_user_id=user_id,approved_by_user_id=None,created_at=_now(),approved_at=None)
        return self.repo.add(row)

    def approve_template(self,template_id:str,user_id:str,*,approval_reason:str)->CommunicationTemplateModel:
        self._require_reviewer(user_id); row=self.session.scalar(select(CommunicationTemplateModel).where(CommunicationTemplateModel.tenant_id==self.tenant_id,CommunicationTemplateModel.template_id==template_id).with_for_update())
        if row is None: raise LookupError("communication template not found")
        if row.status==TemplateStatus.APPROVED.value:return row
        if row.status!=TemplateStatus.DRAFT.value: raise ReviewConflictError("only draft templates may be approved")
        if row.created_by_user_id==user_id: raise ReviewConflictError("template approval requires a different authorized human reviewer")
        row.status=TemplateStatus.APPROVED.value; row.approved_by_user_id=user_id; row.approved_at=_now(); row.change_reason=f"{row.change_reason}\nApproval: {approval_reason}"; return row

    def provision_baseline_templates(self,creator_user_id:str,approver_user_id:str)->list[CommunicationTemplateModel]:
        self._require_reviewer(creator_user_id); self._require_reviewer(approver_user_id)
        if creator_user_id==approver_user_id: raise ReviewConflictError("baseline template governance requires two different human reviewers")
        policy=self._policy(); created=[]
        for locale, localized in policy["localized_templates"].items():
            for channel in ("portal","email","sms"):
                existing=self.repo.approved_template(policy["template_key"],locale,channel)
                if existing: created.append(existing); continue
                row=self.create_template(creator_user_id,template_key=policy["template_key"],template_version=policy["template_version"],locale=locale,channel=channel,subject_template=localized.get("subject") if channel!="sms" else None,body_template=localized["body"],accessibility_schema={"semantic_sections":True,"plain_text_alternative":True,"language":locale,"wcag_target":"2.2-AA"},change_reason="Controlled Release 37 baseline communication template release.")
                created.append(self.approve_template(row.template_id,approver_user_id,approval_reason="Independent human approval of deterministic regulatory communication wording."))
        return created

    def _policy(self)->dict:
        import pathlib
        path=pathlib.Path(__file__).resolve().parents[3]/"config"/"communication_delivery_policy.json"
        return json.loads(path.read_text())

    def _ensure_portal_endpoint(self,notice:DecisionNoticeModel)->CommunicationEndpointModel:
        rows=self.repo.endpoints(notice.claim_id,notice.audience)
        for row in rows:
            if row.channel=="portal":return row
        return self.upsert_endpoint(notice.claim_id,"system-portal-provisioner",audience=notice.audience,channel="portal",destination=f"portal:{notice.claim_id}:{notice.audience}",consent_status=ConsentStatus.REQUIRED_ONLY.value,locale="en",accessibility_preferences={"plain_text":True,"semantic_html":True})

    def _context(self,notice:DecisionNoticeModel,locale:str)->dict:
        payload=notice.rendered_payload; reasons="; ".join(x.get("explanation","") for x in payload.get("reason_explanations",[]))
        appeal=payload.get("appeal_rights",{}); return {"locale":locale,"claim_id":notice.claim_id,"decision":payload.get("decision",""),"decision_summary":payload.get("decision_summary",""),"reasons":reasons,"appeal_rights":f"{appeal.get('instructions','')} Window: {appeal.get('appeal_window_days','')} days.","human_authority_statement":payload.get("human_authority_statement","")}

    def queue_released_notice(self,notice_id:str,*,idempotency_key:str,trace_id:str|None=None)->list[CommunicationDispatchModel]:
        notice=self.post.notice(notice_id)
        if notice is None: raise LookupError("decision notice not found")
        if notice.released_at is None or notice.status not in {DecisionNoticeStatus.DELIVERY_PENDING.value,DecisionNoticeStatus.DELIVERED.value,DecisionNoticeStatus.RELEASED.value}: raise ReviewConflictError("delivery can only be queued for a human-released notice")
        if notice.rendered_payload_sha256!=_sha(notice.rendered_payload): raise ReviewConflictError("released notice payload hash mismatch")
        notification=self.session.scalar(select(DecisionNotificationIntentModel).where(DecisionNotificationIntentModel.tenant_id==self.tenant_id,DecisionNotificationIntentModel.claim_id==notice.claim_id,DecisionNotificationIntentModel.payload_sha256==notice.rendered_payload_sha256).order_by(DecisionNotificationIntentModel.created_at.desc()).limit(1))
        if notification is None: raise ReviewConflictError("released notice has no delivery intent")
        self._ensure_portal_endpoint(notice); endpoints=self.repo.endpoints(notice.claim_id,notice.audience); now=_now(); policy=self._policy(); out=[]
        for endpoint in endpoints:
            if endpoint.channel in {"email","sms"} and endpoint.consent_status==ConsentStatus.OPTED_OUT.value: continue
            template=self.repo.approved_template(policy["template_key"],endpoint.locale,endpoint.channel)
            if template is None:
                self._incident(claim_id=notice.claim_id,dispatch_id=None,severity="high",category="template_governance",summary=f"No approved {endpoint.locale}/{endpoint.channel} template for released notice {notice.notice_id}."); continue
            idem=f"{idempotency_key}:{notice.notice_id}:{endpoint.endpoint_id}:{template.template_id}"
            existing=self.session.scalar(select(CommunicationDispatchModel).where(CommunicationDispatchModel.tenant_id==self.tenant_id,CommunicationDispatchModel.idempotency_key==idem))
            if existing: out.append(existing); continue
            rendered=render_deterministic(template.subject_template,template.body_template,self._context(notice,endpoint.locale)); provider=self.providers.for_channel(endpoint.channel)
            deadline=notice.released_at+timedelta(hours=int(policy["regulatory_notice_delivery_hours"]))
            row=self.repo.add(CommunicationDispatchModel(dispatch_id=f"cd_{uuid4().hex}",tenant_id=self.tenant_id,claim_id=notice.claim_id,notice_id=notice.notice_id,notification_id=notification.notification_id,endpoint_id=endpoint.endpoint_id,template_id=template.template_id,channel=endpoint.channel,provider_name=provider.name,locale=endpoint.locale,status=DispatchStatus.QUEUED.value,rendered_payload=rendered,rendered_payload_sha256=_sha(rendered),idempotency_key=idem,attempt_count=0,next_attempt_at=now,regulatory_deadline_at=deadline,lease_owner=None,lease_until=None,provider_message_id=None,last_error_code=None,trace_id=trace_id,created_at=now,updated_at=now,sent_at=None,delivered_at=None)); out.append(row)
            self._emit(notice.claim_id,"communication.dispatch.queued","communication_dispatch",row.dispatch_id,{"status":row.status,"dispatch_id":row.dispatch_id,"notice_id":notice.notice_id,"channel":row.channel,"provider":row.provider_name,"deadline_status":"open"},trace_id)
        return out

    def lease(self,worker_id:str,*,limit:int=20)->list[CommunicationDispatchModel]:
        now=_now(); rows=self.repo.lease_candidates(now,limit); until=now+timedelta(seconds=self.settings.communication_worker_lease_seconds)
        for row in rows: row.status=DispatchStatus.LEASED.value; row.lease_owner=worker_id; row.lease_until=until; row.updated_at=now
        self.session.flush(); return rows

    def execute(self,dispatch_id:str,worker_id:str)->dict:
        row=self.repo.dispatch(dispatch_id,for_update=True); now=_now()
        if row is None: raise LookupError("communication dispatch not found")
        if row.status!=DispatchStatus.LEASED.value or row.lease_owner!=worker_id or row.lease_until is None or _utc(row.lease_until)<now: raise ReviewConflictError("valid delivery-worker lease required")
        notice=self.post.notice(row.notice_id)
        if notice is None or notice.released_at is None: raise ReviewConflictError("worker cannot deliver a notice that was not human-released")
        if notice.status==DecisionNoticeStatus.DRAFT.value: raise ReviewConflictError("draft notices are not deliverable")
        endpoint=self.repo.endpoint(row.endpoint_id); template=self.session.get(CommunicationTemplateModel,row.template_id)
        if endpoint is None or not endpoint.active: raise ReviewConflictError("communication endpoint is inactive")
        if template is None or template.status!=TemplateStatus.APPROVED.value or template.approved_by_user_id is None: raise ReviewConflictError("approved human-governed template required")
        if row.rendered_payload_sha256!=_sha(row.rendered_payload): raise ReviewConflictError("dispatch payload hash mismatch")
        provider=self.providers.by_name(row.provider_name); destination=self.cipher.decrypt(endpoint.destination_ciphertext)
        with self.tracer.start_as_current_span("communication.dispatch.execute") as span:
            span.set_attribute("communication.channel",row.channel); span.set_attribute("communication.provider",row.provider_name); span.set_attribute("communication.dispatch_id",row.dispatch_id)
            result=provider.send(destination=destination,subject=row.rendered_payload.get("subject"),body=row.rendered_payload.get("body_text",""),idempotency_key=row.idempotency_key,metadata={"dispatch_id":row.dispatch_id,"claim_id":row.claim_id})
        row.attempt_count+=1; row.lease_owner=None; row.lease_until=None; row.updated_at=now
        if result.accepted:
            row.provider_message_id=result.provider_message_id; row.sent_at=row.sent_at or now; row.last_error_code=None
            if row.channel=="portal": row.status=DispatchStatus.DELIVERED.value; row.delivered_at=now
            else: row.status=DispatchStatus.SENT.value
            corr_key=f"transport-dispatch:{row.dispatch_id}"
            corr=self.session.scalar(select(ExternalCorrespondenceModel).where(ExternalCorrespondenceModel.tenant_id==self.tenant_id,ExternalCorrespondenceModel.idempotency_key==corr_key))
            if corr is None:
                self.post.add(ExternalCorrespondenceModel(correspondence_id=f"xc_{uuid4().hex}",tenant_id=self.tenant_id,claim_id=row.claim_id,appeal_id=notice.appeal_id,notice_id=notice.notice_id,direction="outbound",channel=row.channel,audience=notice.audience,external_message_id=result.provider_message_id,payload_sha256=row.rendered_payload_sha256,actor_type="communication_worker",actor_id=worker_id,idempotency_key=corr_key,occurred_at=now))
        else:
            row.last_error_code=result.error_code or "provider_rejected"
            if result.retryable and row.attempt_count<self.settings.communication_max_delivery_attempts:
                delay=min(self.settings.communication_retry_max_seconds,self.settings.communication_retry_base_seconds*(2**(row.attempt_count-1))); row.status=DispatchStatus.RETRY_PENDING.value; row.next_attempt_at=now+timedelta(seconds=delay)
            else:
                row.status=DispatchStatus.DEAD_LETTERED.value; self._incident(claim_id=row.claim_id,dispatch_id=row.dispatch_id,severity="high",category="delivery_dead_letter",summary=f"Dispatch exhausted delivery attempts: {row.last_error_code}")
        self._emit(row.claim_id,"communication.dispatch.updated","communication_dispatch",row.dispatch_id,{"status":row.status,"dispatch_id":row.dispatch_id,"notice_id":row.notice_id,"channel":row.channel,"provider":row.provider_name,"deadline_status":"breached" if now>_utc(row.regulatory_deadline_at) and row.delivered_at is None else "open"},row.trace_id)
        return self.dispatch_view(row)

    def verify_webhook_signature(self,raw_body:bytes,signature:str)->bool:
        expected=hmac.new(self.settings.communication_provider_webhook_secret.get_secret_value().encode(),raw_body,hashlib.sha256).hexdigest(); return hmac.compare_digest(expected,signature)

    def record_receipt(self,provider_name:str,payload:dict,*,signature_verified:bool)->CommunicationReceiptModel:
        if not signature_verified: raise ReviewConflictError("provider webhook signature verification failed")
        if payload.get("tenant_id")!=self.tenant_id: raise ReviewConflictError("provider receipt tenant mismatch")
        existing=self.repo.receipt_by_event(provider_name,payload["provider_event_id"])
        if existing:return existing
        row=self.repo.dispatch(payload["dispatch_id"],for_update=True)
        if row is None or row.provider_name!=provider_name: raise LookupError("provider dispatch not found")
        status=payload["status"]; now=_now(); occurred=now
        if payload.get("occurred_at"):
            try:occurred=datetime.fromisoformat(payload["occurred_at"].replace("Z","+00:00"))
            except ValueError:occurred=now
        receipt=self.repo.add(CommunicationReceiptModel(receipt_id=f"cr_{uuid4().hex}",tenant_id=self.tenant_id,dispatch_id=row.dispatch_id,provider_name=provider_name,provider_event_id=payload["provider_event_id"],provider_message_id=payload.get("provider_message_id"),status=status,payload_sha256=_sha(payload),signature_verified=True,occurred_at=occurred,received_at=now))
        receipt_corr_key=f"provider-receipt:{provider_name}:{payload['provider_event_id']}"
        receipt_corr=self.session.scalar(select(ExternalCorrespondenceModel).where(ExternalCorrespondenceModel.tenant_id==self.tenant_id,ExternalCorrespondenceModel.idempotency_key==receipt_corr_key))
        if receipt_corr is None:
            notice=self.post.notice(row.notice_id)
            self.post.add(ExternalCorrespondenceModel(correspondence_id=f"xc_{uuid4().hex}",tenant_id=self.tenant_id,claim_id=row.claim_id,appeal_id=notice.appeal_id if notice else None,notice_id=row.notice_id,direction="inbound",channel=row.channel,audience="payer_delivery_operations",external_message_id=payload.get("provider_message_id"),payload_sha256=receipt.payload_sha256,actor_type="external_provider",actor_id=provider_name,idempotency_key=receipt_corr_key,occurred_at=now))
        if status==ReceiptStatus.DELIVERED.value:
            row.status=DispatchStatus.DELIVERED.value; row.delivered_at=occurred; row.provider_message_id=payload.get("provider_message_id") or row.provider_message_id
        elif status in {ReceiptStatus.BOUNCED.value,ReceiptStatus.COMPLAINT.value}:
            row.status=DispatchStatus.BOUNCED.value; row.last_error_code=status; self._incident(claim_id=row.claim_id,dispatch_id=row.dispatch_id,severity="high",category=f"provider_{status}",summary=f"Provider reported {status} for dispatch {row.dispatch_id}.")
        elif status==ReceiptStatus.FAILED.value:
            row.last_error_code="provider_failed"
            if row.attempt_count<self.settings.communication_max_delivery_attempts:
                row.status=DispatchStatus.RETRY_PENDING.value; row.next_attempt_at=now+timedelta(seconds=min(self.settings.communication_retry_max_seconds,self.settings.communication_retry_base_seconds*(2**max(0,row.attempt_count))))
            else: row.status=DispatchStatus.DEAD_LETTERED.value
        elif status==ReceiptStatus.ACCEPTED.value: row.status=DispatchStatus.SENT.value
        row.updated_at=now; self._emit(row.claim_id,"communication.receipt.recorded","communication_dispatch",row.dispatch_id,{"status":row.status,"dispatch_id":row.dispatch_id,"notice_id":row.notice_id,"channel":row.channel,"provider":provider_name},row.trace_id); return receipt

    def reconcile_notice(self,notice_id:str,*,idempotency_key:str)->CommunicationReconciliationModel:
        notice=self.post.notice(notice_id)
        if notice is None: raise LookupError("decision notice not found")
        dispatches=self.repo.dispatches(notice_id=notice_id); delivered=[x for x in dispatches if x.status==DispatchStatus.DELIVERED.value]; failed=[x for x in dispatches if x.status in {DispatchStatus.BOUNCED.value,DispatchStatus.FAILED.value,DispatchStatus.DEAD_LETTERED.value}]; now=_now(); gaps=[]
        if not dispatches:gaps.append("no_dispatches")
        if dispatches and not delivered:gaps.append("no_confirmed_delivery")
        if any(_utc(x.regulatory_deadline_at)<now and x.delivered_at is None for x in dispatches):gaps.append("regulatory_delivery_deadline_breached")
        correspondence=self.post.correspondence(notice.claim_id)
        outbound_ids={x.external_message_id for x in correspondence if x.direction=="outbound" and x.external_message_id}
        for dispatch in dispatches:
            if dispatch.provider_message_id and dispatch.provider_message_id not in outbound_ids:gaps.append(f"correspondence_gap:{dispatch.dispatch_id}")
        status="reconciled" if delivered else ("attention_required" if failed or gaps else "pending")
        payload={"notice_id":notice_id,"dispatches":[{"dispatch_id":x.dispatch_id,"channel":x.channel,"status":x.status,"provider_message_id":x.provider_message_id} for x in dispatches],"gaps":gaps,"status":status}
        row=self.repo.add(CommunicationReconciliationModel(reconciliation_id=f"recon_{uuid4().hex}",tenant_id=self.tenant_id,claim_id=notice.claim_id,notice_id=notice_id,status=status,expected_dispatches=len(dispatches),delivered_dispatches=len(delivered),failed_dispatches=len(failed),gaps=gaps,reconciliation_sha256=_sha({"idempotency_key":idempotency_key,**payload}),created_at=now))
        notification=self.session.scalar(select(DecisionNotificationIntentModel).where(DecisionNotificationIntentModel.tenant_id==self.tenant_id,DecisionNotificationIntentModel.claim_id==notice.claim_id,DecisionNotificationIntentModel.payload_sha256==notice.rendered_payload_sha256).order_by(DecisionNotificationIntentModel.created_at.desc()).limit(1))
        if delivered:
            notice.status=DecisionNoticeStatus.DELIVERED.value; notice.updated_at=now
            if notification: notification.status="delivered"; notification.delivered_at=min(x.delivered_at for x in delivered if x.delivered_at)
        elif dispatches and len(failed)==len(dispatches):
            notice.status=DecisionNoticeStatus.DEAD_LETTERED.value; notice.updated_at=now
            if notification:
                notification.status="dead_lettered"
                if self.post.dead_letter(notification.notification_id) is None:
                    self.post.add(CommunicationDeadLetterModel(dead_letter_id=f"cdl_{uuid4().hex}",tenant_id=self.tenant_id,claim_id=notice.claim_id,notification_id=notification.notification_id,reason_code="all_release37_dispatches_terminal",final_error_sha256=_sha([x.last_error_code for x in failed]),attempt_count=sum(x.attempt_count for x in failed),created_at=now))
        self._emit(notice.claim_id,"communication.reconciliation.completed","decision_notice",notice.notice_id,{"status":status,"notice_id":notice.notice_id,"deadline_status":"breached" if "regulatory_delivery_deadline_breached" in gaps else "met"}); return row

    def render_notice_pdf(self,notice_id:str,locale:str="en")->bytes:
        notice=self.post.notice(notice_id)
        if notice is None or notice.released_at is None: raise LookupError("released decision notice not found")
        dispatch=next((x for x in self.repo.dispatches(notice_id=notice_id) if x.locale==locale),None)
        if dispatch is None:
            payload={"sections":[{"heading":"Decision","text":notice.rendered_payload.get("decision_summary","")},{"heading":"Reasons","text":"; ".join(x.get("explanation","") for x in notice.reason_explanations)},{"heading":"Human authority","text":notice.rendered_payload.get("human_authority_statement","")}],"language":locale}
        else: payload=dispatch.rendered_payload
        return render_pdf_bytes(payload)

    def place_legal_hold(self,claim_id:str,user_id:str,reason:str)->CommunicationLegalHoldModel:
        self._require_reviewer(user_id); return self.repo.add(CommunicationLegalHoldModel(hold_id=f"hold_{uuid4().hex}",tenant_id=self.tenant_id,claim_id=claim_id,reason=reason,placed_by_user_id=user_id,placed_at=_now(),released_by_user_id=None,released_at=None,release_reason=None))

    def release_legal_hold(self,hold_id:str,user_id:str,reason:str)->CommunicationLegalHoldModel:
        self._require_reviewer(user_id); row=self.session.scalar(select(CommunicationLegalHoldModel).where(CommunicationLegalHoldModel.tenant_id==self.tenant_id,CommunicationLegalHoldModel.hold_id==hold_id).with_for_update())
        if row is None: raise LookupError("communication legal hold not found")
        if row.released_at is None: row.released_at=_now(); row.released_by_user_id=user_id; row.release_reason=reason
        self.session.flush()
        return row

    def retention_status(self,claim_id:str)->dict:
        holds=self.repo.active_holds(claim_id); history=self.post.history(claim_id); effective=max((_utc(x.effective_at) for x in history),default=_now()); eligible=effective+timedelta(days=self.settings.communication_retention_days)
        return {"claim_id":claim_id,"legal_hold":bool(holds),"active_hold_ids":[x.hold_id for x in holds],"retention_days":self.settings.communication_retention_days,"eligible_for_disposition_at":eligible,"disposition_blocked":bool(holds) or _now()<eligible,"destructive_purge_automatic":False}

    def build_audit_export(self,claim_id:str)->tuple[bytes,str]:
        notices=self.post.notices(claim_id); dispatches=self.repo.dispatches(claim_id=claim_id); history=self.post.history(claim_id); correspondence=self.post.correspondence(claim_id)
        from app.models.appeal_resolution import AppealFinalResolutionModel, AppealResolutionAuditEventModel
        release39=list(self.session.scalars(select(AppealFinalResolutionModel).where(AppealFinalResolutionModel.tenant_id==self.tenant_id,AppealFinalResolutionModel.claim_id==claim_id).order_by(AppealFinalResolutionModel.resolved_at)))
        release39_audit=list(self.session.scalars(select(AppealResolutionAuditEventModel).where(AppealResolutionAuditEventModel.tenant_id==self.tenant_id,AppealResolutionAuditEventModel.claim_id==claim_id).order_by(AppealResolutionAuditEventModel.appeal_id,AppealResolutionAuditEventModel.sequence)))
        manifest={"tenant_id":self.tenant_id,"claim_id":claim_id,"generated_at":_now().isoformat(),"human_authority":"Transport records do not create or alter adjudication authority.","decision_history":[{"sequence":x.sequence,"source_type":x.source_type,"decision":x.decision,"version_sha256":x.version_sha256} for x in history],"appeal_final_resolutions":[{"resolution_id":x.resolution_id,"appeal_id":x.appeal_id,"packet_id":x.packet_id,"outcome":x.outcome,"controlling_decision":x.controlling_decision,"original_approved_amount":str(x.original_approved_amount),"reconsidered_approved_amount":str(x.reconsidered_approved_amount),"financial_delta":str(x.financial_delta),"reconsideration_snapshot_sha256":x.reconsideration_snapshot_sha256,"packet_locked_sha256":x.packet_locked_sha256,"payload_sha256":x.payload_sha256,"history_version_id":x.history_version_id,"notice_id":x.notice_id,"resolved_at":x.resolved_at.isoformat()} for x in release39],"appeal_resolution_audit_chain":[{"appeal_id":x.appeal_id,"sequence":x.sequence,"event_type":x.event_type,"actor_type":x.actor_type,"actor_id":x.actor_id,"previous_event_sha256":x.previous_event_sha256,"event_sha256":x.event_sha256,"occurred_at":x.occurred_at.isoformat()} for x in release39_audit],"notices":[{"notice_id":x.notice_id,"status":x.status,"released_by_user_id":x.released_by_user_id,"rendered_payload_sha256":x.rendered_payload_sha256,"evidence_snapshot_sha256":x.evidence_snapshot_sha256,"appeal_id":x.appeal_id,"resolution_id":x.resolution_id} for x in notices],"dispatches":[self.dispatch_view(x) for x in dispatches],"receipts":[self.receipt_view(r) for d in dispatches for r in self.repo.receipts(d.dispatch_id)],"correspondence":[{"correspondence_id":x.correspondence_id,"direction":x.direction,"channel":x.channel,"payload_sha256":x.payload_sha256,"occurred_at":x.occurred_at.isoformat()} for x in correspondence],"retention":self.retention_status(claim_id)}
        raw=_canonical(manifest); signature=hmac.new(self.settings.security_audit_export_hmac_secret.get_secret_value().encode(),raw,hashlib.sha256).hexdigest(); signed={**manifest,"manifest_sha256":hashlib.sha256(raw).hexdigest(),"manifest_hmac_sha256":signature}
        buf=io.BytesIO()
        with zipfile.ZipFile(buf,"w",zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("manifest.json",json.dumps(signed,indent=2,sort_keys=True,default=str))
            for notice in notices:
                if notice.released_at: zf.writestr(f"notices/{notice.notice_id}.pdf",self.render_notice_pdf(notice.notice_id))
        data=buf.getvalue(); return data,hashlib.sha256(data).hexdigest()

    def recover_dispatch(self,dispatch_id:str,user_id:str,reason:str)->CommunicationDispatchModel:
        self._require_reviewer(user_id); row=self.repo.dispatch(dispatch_id,for_update=True)
        if row is None: raise LookupError("communication dispatch not found")
        if row.status not in {DispatchStatus.DEAD_LETTERED.value,DispatchStatus.BOUNCED.value,DispatchStatus.FAILED.value}: raise ReviewConflictError("only failed terminal dispatches may be recovered")
        row.status=DispatchStatus.RETRY_PENDING.value; row.next_attempt_at=_now(); row.lease_owner=None; row.lease_until=None; row.updated_at=_now()
        for incident in self.repo.incidents(status="open"):
            if incident.dispatch_id==dispatch_id: incident.status="recovered"; incident.recovery_action=f"Human {user_id}: {reason}"; incident.recovered_at=_now()
        self._emit(row.claim_id,"communication.dispatch.recovered","communication_dispatch",row.dispatch_id,{"status":row.status,"dispatch_id":row.dispatch_id,"notice_id":row.notice_id,"channel":row.channel,"provider":row.provider_name}); return row

    def dashboard(self)->dict:
        rows=self.repo.dispatches(); now=_now(); terminal=[x for x in rows if x.status in {DispatchStatus.DELIVERED.value,DispatchStatus.BOUNCED.value,DispatchStatus.DEAD_LETTERED.value,DispatchStatus.FAILED.value}]; delivered=[x for x in rows if x.status==DispatchStatus.DELIVERED.value]; on_time=[x for x in delivered if x.delivered_at and _utc(x.delivered_at)<=_utc(x.regulatory_deadline_at)]
        return {"total_dispatches":len(rows),"queued":sum(x.status in {DispatchStatus.QUEUED.value,DispatchStatus.RETRY_PENDING.value,DispatchStatus.LEASED.value} for x in rows),"sent_waiting_receipt":sum(x.status==DispatchStatus.SENT.value for x in rows),"delivered":len(delivered),"bounced":sum(x.status==DispatchStatus.BOUNCED.value for x in rows),"dead_lettered":sum(x.status==DispatchStatus.DEAD_LETTERED.value for x in rows),"deadline_breaches":sum(_utc(x.regulatory_deadline_at)<now and x.delivered_at is None for x in rows),"delivery_slo_percent":round((len(on_time)/len(terminal)*100),2) if terminal else 100.0,"delivery_slo_target_percent":self.settings.communication_delivery_slo_percent,"open_incidents":len(self.repo.incidents(status="open")),"adjudication_authority":"none"}

    def dispatch_view(self,row:CommunicationDispatchModel)->dict:
        endpoint=self.repo.endpoint(row.endpoint_id)
        return {"dispatch_id":row.dispatch_id,"claim_id":row.claim_id,"notice_id":row.notice_id,"channel":row.channel,"provider_name":row.provider_name,"locale":row.locale,"status":row.status,"destination_fingerprint":endpoint.destination_fingerprint if endpoint else None,"destination_encrypted_at_rest":True,"template_id":row.template_id,"rendered_payload_sha256":row.rendered_payload_sha256,"attempt_count":row.attempt_count,"next_attempt_at":row.next_attempt_at,"regulatory_deadline_at":row.regulatory_deadline_at,"provider_message_id":row.provider_message_id,"sent_at":row.sent_at,"delivered_at":row.delivered_at,"trace_id":row.trace_id}

    @staticmethod
    def receipt_view(row:CommunicationReceiptModel)->dict:
        return {"receipt_id":row.receipt_id,"dispatch_id":row.dispatch_id,"provider_name":row.provider_name,"provider_event_id":row.provider_event_id,"provider_message_id":row.provider_message_id,"status":row.status,"payload_sha256":row.payload_sha256,"signature_verified":row.signature_verified,"occurred_at":row.occurred_at,"received_at":row.received_at}

    def traceability(self,claim_id:str)->dict:
        notices=self.post.notices(claim_id); dispatches=self.repo.dispatches(claim_id=claim_id); history=self.post.history(claim_id); appeals=self.post.appeals(claim_id)
        edges=[]
        for notice in notices: edges.extend([{"from":notice.decision_id,"to":notice.notice_id,"relationship":"human_decision_rendered_as_released_notice"},{"from":notice.evidence_snapshot_sha256,"to":notice.notice_id,"relationship":"notice_bound_to_locked_evidence_snapshot"}])
        for d in dispatches:
            edges.append({"from":d.notice_id,"to":d.dispatch_id,"relationship":"human_released_notice_dispatched"})
            for r in self.repo.receipts(d.dispatch_id):edges.append({"from":d.dispatch_id,"to":r.receipt_id,"relationship":"provider_delivery_receipt"})
        for appeal in appeals:edges.append({"from":appeal.notice_id,"to":appeal.appeal_id,"relationship":"released_notice_may_be_appealed"})
        return {"claim_id":claim_id,"decision_history_versions":[x.version_sha256 for x in history],"edges":edges,"provider_and_worker_adjudication_authority":False,"original_and_appeal_human_authority_preserved":True}
