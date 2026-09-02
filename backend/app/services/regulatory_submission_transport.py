from __future__ import annotations
import base64,hashlib,hmac,json,os
from datetime import UTC,datetime,timedelta
from uuid import uuid4
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy.orm import Session
from app.domain.regulatory_submission_transport import REGULATORY_TRANSPORT_AUTHORITY
from app.domain.realtime import EventEnvelope,EventTopic
from app.models.regulatory_submission_transport import *
from app.integrations.regulatory_transport import RegulatoryTransportRequest,adapter_for
from app.realtime.events import enqueue_realtime_event
from app.observability.metrics import record_regulatory_transport
from app.repositories.regulatory_submission_transport import RegulatorySubmissionTransportRepository
from app.repositories.recovery_control_assurance import RecoveryControlAssuranceRepository
from app.repositories.tenancy import MembershipRepository
from app.services.review_workbench import ReviewConflictError


def _now():return datetime.now(UTC)
def _canon(v):return json.dumps(v,sort_keys=True,separators=(",",":"),default=str)
def _sha(v):return hashlib.sha256((v if isinstance(v,str) else _canon(v)).encode()).hexdigest()
def _secret(name,default):return hashlib.sha256(os.getenv(name,default).encode()).digest()
def _utc(v):
    if v is None:return None
    return v.replace(tzinfo=UTC) if v.tzinfo is None else v.astimezone(UTC)

class RegulatorySubmissionTransportService:
    READ_ROLES={"auditor","tenant_admin","accounting_controller"}; RELEASE_ROLES={"auditor","tenant_admin"}; REGISTRY_ROLES={"tenant_admin","auditor"}
    def __init__(self,session:Session,tenant_id:str):
        self.session=session;self.tenant_id=tenant_id;self.repo=RegulatorySubmissionTransportRepository(session,tenant_id);self.control=RecoveryControlAssuranceRepository(session,tenant_id);self.members=MembershipRepository(session,tenant_id)
    def _role(self,user_id,allowed,msg):
        m=self.members.get_by_user(user_id)
        if m is None or m.status!="active" or m.role not in allowed:raise ReviewConflictError(msg)
        return m
    def create_destination(self,user_id,**x):
        self._role(user_id,self.REGISTRY_ROLES,"authorized human regulatory registry role required")
        if x["transport_type"] not in {"sandbox_api","sftp","https_api"}:raise ReviewConflictError("unsupported regulatory transport type")
        row=self.repo.add(RegulatoryDestinationModel(destination_id=f"rdst_{uuid4().hex}",tenant_id=self.tenant_id,active=True,failure_streak=0,circuit_open_until=None,last_failure_at=None,created_by_user_id=user_id,created_at=_now(),**x));self._emit("regulatory_transport.destination.registered",row.destination_id,{"destination_key":row.destination_key});return row
    def release(self,package_id,user_id,*,destination_id,schema_name,schema_version,release_reason,idempotency_key):
        self._role(user_id,self.RELEASE_ROLES,"authorized human regulatory release role required")
        if (existing:=self.repo.release_for_package(package_id)):return existing
        p=self.control.package(package_id);cert=self.control.certification(package_id);dest=self.repo.destination(destination_id)
        if p is None:raise LookupError("submission package not found")
        if cert is None or p.status!="certified":raise ReviewConflictError("Human certification required before transport release")
        if not p.locked_manifest_sha256 or cert.locked_manifest_sha256!=p.locked_manifest_sha256:raise ReviewConflictError("certification/manifest hash mismatch")
        if dest is None or not dest.active:raise ReviewConflictError("active regulatory destination required")
        if dest.schema_name!=schema_name or dest.schema_version!=schema_version:raise ReviewConflictError("destination schema/version validation failed")
        payload={"package_id":package_id,"package_version":p.package_version,"locked_manifest_sha256":p.locked_manifest_sha256,"certification_id":cert.certification_id,"certification_sha256":cert.certification_sha256,"destination_id":destination_id,"schema_name":schema_name,"schema_version":schema_version,"released_by":user_id,"reason":release_reason}
        rel=self.repo.add(RegulatorySubmissionReleaseModel(release_id=f"rsrel_{uuid4().hex}",tenant_id=self.tenant_id,package_id=package_id,certification_id=cert.certification_id,destination_id=destination_id,package_version=p.package_version,locked_manifest_sha256=p.locked_manifest_sha256,certification_sha256=cert.certification_sha256,schema_name=schema_name,schema_version=schema_version,release_reason=release_reason,released_by_user_id=user_id,release_sha256=_sha(payload),idempotency_key=idempotency_key,released_at=_now()))
        env={"release_id":rel.release_id,"package_id":p.package_id,"package_version":p.package_version,"manifest":p.manifest,"locked_manifest_sha256":p.locked_manifest_sha256,"certification_sha256":cert.certification_sha256,"schema_name":schema_name,"schema_version":schema_version,"correction_of_package_id":p.correction_of_package_id}
        plain=_canon(env).encode();nonce=os.urandom(12);enc=AESGCM(_secret("REGULATORY_TRANSPORT_ENCRYPTION_KEY","medclaimiq-release50-development-encryption")).encrypt(nonce,plain,destination_id.encode());encrypted=base64.b64encode(enc).decode();nonce_b64=base64.b64encode(nonce).decode();sig=hmac.new(_secret("REGULATORY_TRANSPORT_SIGNING_SECRET","medclaimiq-release50-development-signing"),plain,hashlib.sha256).hexdigest()
        supersedes=None
        if p.correction_of_package_id:
            prior_release=self.repo.release_for_package(p.correction_of_package_id)
            if prior_release:
                prior_tx=self.repo.transmission_for_release(prior_release.release_id)
                supersedes=prior_tx.transmission_id if prior_tx else None
        tx=self.repo.add(RegulatoryTransmissionModel(transmission_id=f"rtx_{uuid4().hex}",tenant_id=self.tenant_id,release_id=rel.release_id,package_id=package_id,destination_id=destination_id,supersedes_transmission_id=supersedes,dispatch_key=_sha({"release":rel.release_id,"dest":destination_id}),encrypted_envelope=encrypted,nonce_b64=nonce_b64,envelope_signature=sig,envelope_sha256=_sha(plain),status="queued",attempt_count=0,max_attempts=5,next_attempt_at=_now(),lease_owner=None,lease_expires_at=None,provider_message_id=None,external_submission_reference=None,deadline_at=_now()+timedelta(hours=24),created_at=_now(),updated_at=_now()))
        p.status="staged";p.staged_at=rel.released_at;self.session.flush();self._audit(tx,"submission.release.authorized","human_regulatory_release",user_id,{"release_sha256":rel.release_sha256});self._emit("regulatory_transport.release.authorized",tx.transmission_id,{"package_id":package_id});return rel
    def lease_and_dispatch(self,worker_id:str):
        # Worker executes only already-human-released transmissions; never creates releases.
        now=_now();eligible=[]
        for x in self.repo.transmissions():
            if x.status not in {"queued","retry_pending"}:continue
            if x.next_attempt_at is not None and _utc(x.next_attempt_at)>now:continue
            if x.lease_expires_at is not None and _utc(x.lease_expires_at)>now:continue
            dest=self.repo.destination(x.destination_id)
            if dest and dest.circuit_open_until is not None and _utc(dest.circuit_open_until)>now:continue
            eligible.append(x)
        if not eligible:return None
        tx=self.repo.transmission(eligible[-1].transmission_id,for_update=True);dest=self.repo.destination(tx.destination_id)
        tx.lease_owner=worker_id;tx.lease_expires_at=now+timedelta(minutes=5);tx.status="leased";tx.updated_at=now;self.session.flush()
        tx.attempt_count+=1
        try:
            rel=self.repo.release(tx.release_id)
            result=adapter_for(dest.transport_type).send(RegulatoryTransportRequest(dispatch_key=tx.dispatch_key,destination_key=dest.destination_key,endpoint_reference=dest.endpoint_reference,encrypted_envelope=tx.encrypted_envelope,envelope_signature=tx.envelope_signature,schema_name=rel.schema_name,schema_version=rel.schema_version))
            tx.provider_message_id=result.provider_message_id;tx.external_submission_reference=result.external_submission_reference;tx.status="sent";tx.next_attempt_at=None;tx.lease_owner=None;tx.lease_expires_at=None;tx.updated_at=_now();dest.failure_streak=0;dest.circuit_open_until=None
            payload={"tx":tx.transmission_id,"attempt":tx.attempt_count,"status":"sent","provider_message_id":tx.provider_message_id,"external_submission_reference":tx.external_submission_reference}
            self.repo.add(RegulatoryDeliveryAttemptModel(attempt_id=f"rda_{uuid4().hex}",tenant_id=self.tenant_id,transmission_id=tx.transmission_id,attempt_sequence=tx.attempt_count,worker_id=worker_id,status="sent",provider_message_id=tx.provider_message_id,external_submission_reference=tx.external_submission_reference,error_code=None,error_message=None,next_retry_at=None,payload_sha256=_sha(payload),attempted_at=_now()))
            self.session.flush();self._audit(tx,"transport.sent","delivery_worker",worker_id,{"attempt":tx.attempt_count,"provider_message_id":tx.provider_message_id});self._emit("regulatory_transport.transmission.sent",tx.transmission_id,{"attempt_count":tx.attempt_count});record_regulatory_transport(metric="transmission_sent",value=1,attributes={"tenant_id":self.tenant_id,"destination_id":tx.destination_id});return tx
        except Exception as e:
            dest.failure_streak=(dest.failure_streak or 0)+1;dest.last_failure_at=_now();tx.lease_owner=None;tx.lease_expires_at=None;tx.updated_at=_now();retry_at=None
            if dest.failure_streak>=3:
                dest.circuit_open_until=_now()+timedelta(minutes=5)
            if tx.attempt_count>=tx.max_attempts:
                tx.status="dead_lettered";self.repo.add(RegulatoryTransportIncidentModel(incident_id=f"rti_{uuid4().hex}",tenant_id=self.tenant_id,transmission_id=tx.transmission_id,incident_type="delivery_dlq",status="open",details={"error":str(e)},created_at=_now(),resolved_at=None))
            else:
                tx.status="retry_pending";retry_at=_now()+timedelta(seconds=min(3600,30*(2**max(0,tx.attempt_count-1))));tx.next_attempt_at=retry_at
            payload={"tx":tx.transmission_id,"attempt":tx.attempt_count,"status":tx.status,"error":str(e),"next_retry_at":retry_at}
            self.repo.add(RegulatoryDeliveryAttemptModel(attempt_id=f"rda_{uuid4().hex}",tenant_id=self.tenant_id,transmission_id=tx.transmission_id,attempt_sequence=tx.attempt_count,worker_id=worker_id,status=tx.status,provider_message_id=None,external_submission_reference=None,error_code="transport_error",error_message=str(e),next_retry_at=retry_at,payload_sha256=_sha(payload),attempted_at=_now()))
            self.session.flush();self._audit(tx,"transport.failed","delivery_worker",worker_id,{"attempt":tx.attempt_count,"status":tx.status,"circuit_open":bool(dest.circuit_open_until)});return tx

    def acknowledgment(self,*,destination_id,external_event_id,external_submission_reference,acknowledgment_status,receipt_payload,signature,rejection_code=None,rejection_reason=None):
        if (existing:=self.repo.ack_by_event(destination_id,external_event_id)):return existing
        tx=next((x for x in self.repo.transmissions() if x.destination_id==destination_id and x.external_submission_reference==external_submission_reference),None)
        if tx is None:raise LookupError("transmission for acknowledgment not found")
        signed=_canon({"destination_id":destination_id,"external_event_id":external_event_id,"external_submission_reference":external_submission_reference,"acknowledgment_status":acknowledgment_status,"receipt_payload":receipt_payload,"rejection_code":rejection_code,"rejection_reason":rejection_reason}).encode();expected=hmac.new(_secret("REGULATORY_ACK_WEBHOOK_SECRET","medclaimiq-release50-development-ack"),signed,hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected,signature):raise ReviewConflictError("invalid regulatory acknowledgment signature")
        if acknowledgment_status not in {"accepted","rejected","received","processing"}:raise ReviewConflictError("unsupported acknowledgment status")
        ack=self.repo.add(RegulatoryAcknowledgmentModel(acknowledgment_id=f"rack_{uuid4().hex}",tenant_id=self.tenant_id,transmission_id=tx.transmission_id,destination_id=destination_id,external_event_id=external_event_id,external_submission_reference=external_submission_reference,acknowledgment_status=acknowledgment_status,rejection_code=rejection_code,rejection_reason=rejection_reason,receipt_payload=receipt_payload,signature_verified=True,receipt_sha256=_sha(signed),received_at=_now()))
        tx.status={"accepted":"acknowledged","rejected":"rejected"}.get(acknowledgment_status,"awaiting_ack");tx.updated_at=_now();dest=self.repo.destination(destination_id);dest.failure_streak=0;dest.circuit_open_until=None;p=self.control.package(tx.package_id);p.status="submitted";p.submitted_at=ack.received_at;self.session.flush()
        if acknowledgment_status=="rejected":self.repo.add(RegulatoryTransportIncidentModel(incident_id=f"rti_{uuid4().hex}",tenant_id=self.tenant_id,transmission_id=tx.transmission_id,incident_type="regulator_rejection",status="open",details={"code":rejection_code,"reason":rejection_reason},created_at=_now(),resolved_at=None))
        self._audit(tx,"acknowledgment.received","external_regulator",destination_id,{"status":acknowledgment_status,"receipt_sha256":ack.receipt_sha256});self._emit("regulatory_transport.acknowledgment.received",tx.transmission_id,{"status":acknowledgment_status});record_regulatory_transport(metric="acknowledgment",value=1,attributes={"tenant_id":self.tenant_id,"status":acknowledgment_status});return ack
    def recover(self,transmission_id,user_id,*,rationale):
        self._role(user_id,self.RELEASE_ROLES,"authorized human regulatory recovery role required");tx=self.repo.transmission(transmission_id,for_update=True)
        if tx is None:raise LookupError("transmission not found")
        if tx.status not in {"dead_lettered","rejected"}:raise ReviewConflictError("only rejected or DLQ transmissions may be recovered")
        tx.status="retry_pending";tx.attempt_count=0;tx.next_attempt_at=_now();tx.updated_at=_now();dest=self.repo.destination(tx.destination_id);dest.failure_streak=0;dest.circuit_open_until=None;self.session.flush();self._audit(tx,"transport.recovery.authorized","human_regulatory_recovery",user_id,{"rationale":rationale});return tx
    def dashboard(self,user_id):
        self._role(user_id,self.READ_ROLES,"regulatory transport read role required");txs=self.repo.transmissions();incs=self.repo.incidents();now=_now()
        record_regulatory_transport(metric="sla_breached",value=sum(bool(x.deadline_at and _utc(x.deadline_at)<now and x.status!="acknowledged") for x in txs),attributes={"tenant_id":self.tenant_id});return {"authority":REGULATORY_TRANSPORT_AUTHORITY,"kpis":{"transmissions":len(txs),"acknowledged":sum(x.status=="acknowledged" for x in txs),"rejected":sum(x.status=="rejected" for x in txs),"dlq":sum(x.status=="dead_lettered" for x in txs),"sla_breached":sum(bool(x.deadline_at and _utc(x.deadline_at)<now and x.status!="acknowledged") for x in txs)},"transmissions":[self._view(x) for x in txs],"incidents":[{"incident_id":x.incident_id,"type":x.incident_type,"status":x.status,"details":x.details} for x in incs]}
    def traceability(self,transmission_id,user_id):
        self._role(user_id,self.READ_ROLES,"regulatory transport read role required");tx=self.repo.transmission(transmission_id)
        if tx is None:raise LookupError("transmission not found")
        rel=self.repo.release(tx.release_id);p=self.control.package(tx.package_id);cert=self.control.certification(tx.package_id)
        return {"transmission":self._view(tx),"supersedes_transmission_id":tx.supersedes_transmission_id,"delivery_attempts":[{"attempt_sequence":a.attempt_sequence,"status":a.status,"payload_sha256":a.payload_sha256,"next_retry_at":a.next_retry_at} for a in self.repo.attempts(transmission_id)],"release":{"release_id":rel.release_id,"release_sha256":rel.release_sha256,"released_by_user_id":rel.released_by_user_id},"package":{"package_id":p.package_id,"package_version":p.package_version,"correction_of_package_id":p.correction_of_package_id,"locked_manifest_sha256":p.locked_manifest_sha256},"certification":{"certification_id":cert.certification_id,"certification_sha256":cert.certification_sha256},"acknowledgments":[{"status":a.acknowledgment_status,"external_event_id":a.external_event_id,"receipt_sha256":a.receipt_sha256,"signature_verified":a.signature_verified} for a in self.repo.acknowledgments(transmission_id)],"audit_chain":[{"sequence":a.sequence,"event_type":a.event_type,"event_sha256":a.event_sha256,"previous_event_sha256":a.previous_event_sha256} for a in self.repo.audit(transmission_id)],"provenance":"certified report -> one-time human release -> encrypted signed envelope -> worker transport -> cryptographically verified acknowledgment -> correction/amendment lineage","authority":REGULATORY_TRANSPORT_AUTHORITY}
    def _view(self,x):return {"transmission_id":x.transmission_id,"package_id":x.package_id,"destination_id":x.destination_id,"supersedes_transmission_id":x.supersedes_transmission_id,"status":x.status,"attempt_count":x.attempt_count,"provider_message_id":x.provider_message_id,"external_submission_reference":x.external_submission_reference,"envelope_sha256":x.envelope_sha256,"deadline_at":x.deadline_at,"updated_at":x.updated_at}
    def _audit(self,tx,event_type,actor_type,actor_id,details):
        chain=self.repo.audit(tx.transmission_id);seq=len(chain)+1;prev=chain[-1].event_sha256 if chain else None;payload={"transmission_id":tx.transmission_id,"sequence":seq,"event_type":event_type,"actor_type":actor_type,"actor_id":actor_id,"details":details,"previous":prev};self.repo.add(RegulatoryTransmissionAuditEventModel(audit_event_id=f"rta_{uuid4().hex}",tenant_id=self.tenant_id,transmission_id=tx.transmission_id,sequence=seq,event_type=event_type,actor_type=actor_type,actor_id=actor_id,details=details,previous_event_sha256=prev,event_sha256=_sha(payload),occurred_at=_now()))
    def _emit(self,event_type,aggregate_id,payload):enqueue_realtime_event(self.session,envelope=EventEnvelope(event_id=f"rt_{uuid4().hex}",event_type=event_type,tenant_id=self.tenant_id,claim_id=None,aggregate_type="regulatory_submission_transport",aggregate_id=str(aggregate_id),occurred_at=_now(),producer="medclaimiq-regulatory-transport",payload=payload,metadata={"human_release_required":True,"worker_authority":"transport_execution_only","fund_movement":False}),topic=EventTopic.CLAIMS.value)
