from __future__ import annotations
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.domain.access import AccessRequest, Permission, ResourceAccessContext, ResourceType, UserRole
from app.domain.claims import EvidenceSourceType
from app.models.claims import AuditEventModel, ClaimStatusEventModel
from app.models.fhir import HospitalCrossVerificationModel
from app.models.ingestion import EvidenceUploadSessionModel
from app.models.portal import PortalActionEventModel, PortalDocumentRequestModel, PortalSubmissionModel
from app.models.sla import SLATimerModel
from app.repositories.portal import PortalRepository
from app.repositories.claims import ClaimRepository
from app.services.authorization import authorization_service
from app.services.ingestion import EvidenceIngestionService
from app.schemas.ingestion import UploadInitiateRequest
from app.domain.realtime import EventEnvelope, EventTopic
from app.realtime.events import enqueue_realtime_event

SAFE_STATUS_LABELS={
 "submitted":"Submitted","quarantined":"Files received","extracting":"Processing documents","normalizing":"Processing documents",
 "verifying":"Verification in progress","pending_evidence":"More information needed","ai_reviewed":"Review in progress",
 "human_review":"Review in progress","completed":"Review completed","appeal_ready":"Appeal information available",
 "processing_failed":"Processing needs attention","cancelled":"Cancelled","rejected_at_ingestion":"File processing issue",
}
SAFE_EVENT_PREFIXES=("claim.","portal.","evidence.upload.","evidence.ingestion.","healthcare.claim.cross_verified","sla.timer.")


def _now(): return datetime.now(timezone.utc)

class PortalAccessError(ValueError): pass

class PortalService:
    def __init__(self,session:Session,tenant_id:str,*,storage=None,bucket_name:str="",presign_ttl_seconds:int=900,global_max_file_bytes:int=50_000_000):
        self.session=session; self.tenant_id=tenant_id; self.repo=PortalRepository(session,tenant_id)
        self.storage=storage; self.bucket_name=bucket_name; self.presign_ttl_seconds=presign_ttl_seconds; self.global_max_file_bytes=global_max_file_bytes

    def require_external_role(self,principal):
        if principal.role not in {UserRole.PATIENT,UserRole.PROVIDER,UserRole.HOSPITAL_ADMIN}:
            raise PortalAccessError("patient/provider portal role is required")

    def authorize_claim(self,principal,claim_id:str,permission:Permission=Permission.CLAIM_READ):
        self.require_external_role(principal)
        claim=self.repo.claim(claim_id)
        if claim is None: raise LookupError("claim was not found")
        resource=ResourceAccessContext(resource_type=ResourceType.CLAIM,resource_id=claim.claim_id,owner_tenant_id=claim.tenant_id,
            owner_patient_subject_id=claim.patient_subject_id,related_provider_organization_id=claim.provider_organization_id,assigned_reviewer_user_id=claim.assigned_reviewer_user_id)
        decision=authorization_service.evaluate(AccessRequest(principal=principal,permission=permission,resource=resource))
        if not decision.allowed: raise PortalAccessError("claim access is outside the portal relationship scope")
        return claim

    def list_claims(self,principal):
        self.require_external_role(principal)
        if principal.role is UserRole.PATIENT:
            if not principal.patient_subject_id: return []
            rows=self.repo.patient_claims(principal.patient_subject_id)
        else:
            if not principal.provider_organization_id: return []
            rows=self.repo.provider_claims(principal.provider_organization_id)
        result=[]
        for c in rows:
            reqs=self.repo.requests(c.claim_id); timers=list(self.session.scalars(select(SLATimerModel).where(SLATimerModel.tenant_id==self.tenant_id,SLATimerModel.claim_id==c.claim_id,SLATimerModel.status=="scheduled").order_by(SLATimerModel.due_at)))
            result.append({"claim_id":c.claim_id,"external_claim_ref":c.external_claim_ref,"status":c.status,"total_amount":str(c.total_amount),"currency":c.currency,"service_from":c.service_from,"service_to":c.service_to,"outstanding_request_count":sum(1 for r in reqs if r.status in {"open","responded"}),"next_deadline_at":timers[0].due_at if timers else None})
        return result

    def snapshot(self,principal,claim_id:str):
        claim=self.authorize_claim(principal,claim_id)
        requests=self.repo.requests(claim_id); submissions=self.repo.submissions(claim_id); now=_now()
        verification=self.session.scalar(select(HospitalCrossVerificationModel).where(HospitalCrossVerificationModel.tenant_id==self.tenant_id,HospitalCrossVerificationModel.claim_id==claim_id).order_by(HospitalCrossVerificationModel.created_at.desc()).limit(1))
        timers=list(self.session.scalars(select(SLATimerModel).where(SLATimerModel.tenant_id==self.tenant_id,SLATimerModel.claim_id==claim_id,SLATimerModel.status.in_(["scheduled","breached"])).order_by(SLATimerModel.due_at)))
        timeline=[]
        for e in self.session.scalars(select(ClaimStatusEventModel).where(ClaimStatusEventModel.tenant_id==self.tenant_id,ClaimStatusEventModel.claim_id==claim_id).order_by(ClaimStatusEventModel.occurred_at)):
            timeline.append({"at":e.occurred_at,"type":"claim.status","summary":SAFE_STATUS_LABELS.get(e.to_status,"Claim updated")})
        for e in self.session.scalars(select(AuditEventModel).where(AuditEventModel.tenant_id==self.tenant_id,AuditEventModel.resource_type=="claim",AuditEventModel.resource_id==claim_id,AuditEventModel.action.in_(["claim.created","evidence.created"]).order_by(AuditEventModel.occurred_at))):
            timeline.append({"at":e.occurred_at,"type":e.action,"summary":"Claim created" if e.action=="claim.created" else "Document accepted"})
        timeline.sort(key=lambda x:x["at"])
        return {
          "claim_id":claim.claim_id,"external_claim_ref":claim.external_claim_ref,"status":claim.status,"status_label":SAFE_STATUS_LABELS.get(claim.status,"In progress"),
          "total_amount":str(claim.total_amount),"currency":claim.currency,"service_from":claim.service_from,"service_to":claim.service_to,
          "document_requests":[{"request_id":r.request_id,"requested_document_types":r.requested_document_types,"instructions":r.instructions,"status":r.status,"due_at":r.due_at,"created_at":r.created_at} for r in requests],
          "submissions":[{"submission_id":s.submission_id,"request_id":s.request_id,"document_type":s.document_type,"status":s.status,"acknowledgement_code":s.acknowledgement_code,"upload_session_id":s.upload_session_id,"evidence_id":s.evidence_id,"created_at":s.created_at,"received_at":s.received_at} for s in submissions],
          "verification": {"status":verification.status if verification else "pending","confidence":str(verification.confidence) if verification else None,"message":"Hospital/provider verification completed." if verification else "Verification is still in progress."},
          "deadlines":[{"timer_type":t.timer_type,"status":t.status,"due_at":t.due_at,"seconds_remaining":int((t.due_at-now).total_seconds())} for t in timers],
          "safe_timeline":timeline[-100:],
          "privacy_notice":"This portal intentionally does not expose internal fraud signals, agent reasoning, reviewer notes, or decision-support internals.",
        }

    def create_document_request(self,claim_id:str,reviewer_user_id:str,decision_id:str,requested_document_types:list[str],instructions:str,*,due_at=None):
        existing=self.repo.request_by_decision(decision_id)
        if existing: return existing
        return self.repo.add(PortalDocumentRequestModel(request_id=f"pdr_{uuid4().hex}",tenant_id=self.tenant_id,claim_id=claim_id,source_decision_id=decision_id,requested_by_user_id=reviewer_user_id,requested_document_types=requested_document_types,instructions=instructions,status="open",due_at=due_at,created_at=_now(),updated_at=_now()))

    def initiate_request_upload(self,principal,claim_id:str,request_id:str,payload:UploadInitiateRequest,*,idempotency_key:str,trace_id:str|None=None):
        self.authorize_claim(principal,claim_id,Permission.EVIDENCE_UPLOAD)
        req=self.repo.request(request_id)
        if req is None or req.claim_id!=claim_id or req.status not in {"open","responded"}: raise LookupError("open document request was not found")
        prior=self.repo.submission_by_idempotency(idempotency_key)
        if self.storage is None: raise RuntimeError("object storage is required")
        ingestion=EvidenceIngestionService(self.session,self.tenant_id,storage=self.storage,bucket_name=self.bucket_name,presign_ttl_seconds=self.presign_ttl_seconds,global_max_file_bytes=self.global_max_file_bytes)
        if prior:
            upload,signed=ingestion.initiate_upload(claim_id=claim_id,user_id=principal.user_id,source_type=EvidenceSourceType.PROVIDER_UPLOAD if principal.role in {UserRole.PROVIDER,UserRole.HOSPITAL_ADMIN} else EvidenceSourceType.USER_UPLOAD,idempotency_key=f"portal-upload:{idempotency_key}",payload=payload,trace_id=trace_id)
            return prior,upload,signed
        source=EvidenceSourceType.PROVIDER_UPLOAD if principal.role in {UserRole.PROVIDER,UserRole.HOSPITAL_ADMIN} else EvidenceSourceType.USER_UPLOAD
        upload,signed=ingestion.initiate_upload(claim_id=claim_id,user_id=principal.user_id,source_type=source,idempotency_key=f"portal-upload:{idempotency_key}",payload=payload,trace_id=trace_id)
        row=self.repo.add(PortalSubmissionModel(submission_id=f"psub_{uuid4().hex}",tenant_id=self.tenant_id,claim_id=claim_id,request_id=request_id,submitted_by_user_id=principal.user_id,upload_session_id=upload.upload_session_id,document_type=payload.document_type,status="upload_pending",acknowledgement_code=f"MCQ-{uuid4().hex[:12].upper()}",idempotency_key=idempotency_key,created_at=_now(),updated_at=_now()))
        self._event(claim_id,principal.user_id,"portal.document_upload.initiated",f"portal-init:{idempotency_key}",{"request_id":request_id,"submission_id":row.submission_id},trace_id)
        return row,upload,signed

    def complete_request_upload(self,principal,claim_id:str,request_id:str,upload_session_id:str,*,trace_id:str|None=None):
        self.authorize_claim(principal,claim_id,Permission.EVIDENCE_UPLOAD)
        req=self.repo.request(request_id); sub=self.repo.submission_by_upload(upload_session_id)
        if req is None or req.claim_id!=claim_id or sub is None or sub.request_id!=request_id: raise LookupError("portal submission was not found")
        if sub.submitted_by_user_id != principal.user_id: raise PortalAccessError("only the submitting identity may complete this upload")
        ingestion=EvidenceIngestionService(self.session,self.tenant_id,storage=self.storage,bucket_name=self.bucket_name,presign_ttl_seconds=self.presign_ttl_seconds,global_max_file_bytes=self.global_max_file_bytes)
        upload,event=ingestion.complete_upload(upload_session_id)
        sub.status="received_for_security_processing"; sub.received_at=_now(); sub.updated_at=_now(); req.status="responded"; req.responded_at=_now(); req.updated_at=_now()
        self._event(claim_id,principal.user_id,"portal.document_upload.received",f"portal-complete:{upload_session_id}",{"request_id":request_id,"submission_id":sub.submission_id,"acknowledgement_code":sub.acknowledgement_code},trace_id)
        return sub,upload,event

    def sync_submission_status(self,principal,claim_id:str,submission_id:str):
        self.authorize_claim(principal,claim_id)
        sub=self.session.get(PortalSubmissionModel,submission_id)
        if sub is None or sub.tenant_id!=self.tenant_id or sub.claim_id!=claim_id: raise LookupError("submission was not found")
        upload=self.session.get(EvidenceUploadSessionModel,sub.upload_session_id)
        if upload:
            sub.evidence_id=upload.evidence_id
            if upload.status in {"accepted","finalized"} or upload.evidence_id: sub.status="accepted"
            elif upload.status in {"rejected","failed"}: sub.status="rejected"
            elif upload.status not in {"initiated","uploaded"}: sub.status=upload.status
        return sub

    def _event(self,claim_id,actor_user_id,event_type,idempotency_key,payload,trace_id=None):
        prior=self.repo.event_by_idempotency(idempotency_key)
        if prior:return prior
        now=_now(); row=self.repo.add(PortalActionEventModel(event_id=f"pevt_{uuid4().hex}",tenant_id=self.tenant_id,claim_id=claim_id,actor_user_id=actor_user_id,event_type=event_type,idempotency_key=idempotency_key,payload=payload,trace_id=trace_id,occurred_at=now))
        enqueue_realtime_event(self.session,envelope=EventEnvelope(event_id=row.event_id,event_type=event_type,tenant_id=self.tenant_id,claim_id=claim_id,aggregate_type="external_portal",aggregate_id=claim_id,occurred_at=now,trace_id=trace_id,producer="medclaimiq-external-portal",payload=payload),topic=EventTopic.CLAIMS.value)
        return row
