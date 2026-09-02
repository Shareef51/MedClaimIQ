from __future__ import annotations
import hashlib, json
from datetime import UTC, datetime
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.agents.model_client import StructuredModelClient
from app.domain.regulatory_examination import REGULATORY_EXAMINATION_AUTHORITY
from app.integrations.regulatory_correspondence import RegulatoryCorrespondenceAdapter, SandboxSecureRegulatoryCorrespondenceAdapter
from app.domain.realtime import EventEnvelope, EventTopic
from app.models.regulatory_examination import *
from app.observability.metrics import record_regulatory_examination
from app.realtime.events import enqueue_realtime_event
from app.repositories.recovery_control_assurance import RecoveryControlAssuranceRepository
from app.repositories.regulatory_examination import RegulatoryExaminationRepository
from app.repositories.regulatory_supervisory_control import RegulatorySupervisoryControlRepository
from app.repositories.tenancy import MembershipRepository
from app.services.regulatory_supervisory_control import RegulatorySupervisoryControlService
from app.services.review_workbench import ReviewConflictError
from app.schemas.regulatory_examination import AIResponseDraft

def _now(): return datetime.now(UTC)
def _canon(v): return json.dumps(v,sort_keys=True,separators=(",",":"),default=str)
def _sha(v): return hashlib.sha256((v if isinstance(v,str) else _canon(v)).encode()).hexdigest()
def _utc(v):
    if v is None:return None
    return v.replace(tzinfo=UTC) if v.tzinfo is None else v.astimezone(UTC)

class RegulatoryExaminationService:
    READ_ROLES={"auditor","tenant_admin","accounting_controller"}
    PREPARER_ROLES={"auditor","tenant_admin","accounting_controller"}
    CHECKER_ROLES={"auditor","tenant_admin"}
    INQUIRY_TYPES={"examination","inquiry","document_request","follow_up","supervisory_review"}
    QUESTION_CLASSES={"financial_reporting","accounting_tieout","recovery_controls","submission_transport","data_quality","policy_governance","other"}
    FINDING_SEVERITIES={"low","medium","high","critical"}
    SECURE_CHANNELS={"regulator_portal","sftp_reference","encrypted_email","secure_api_reference"}
    def __init__(self,session:Session,tenant_id:str,*,model_client:StructuredModelClient|None=None,response_model:str="gpt-5.6-terra",correspondence_adapter:RegulatoryCorrespondenceAdapter|None=None):
        self.session=session;self.tenant_id=tenant_id;self.repo=RegulatoryExaminationRepository(session,tenant_id);self.super_repo=RegulatorySupervisoryControlRepository(session,tenant_id);self.control=RecoveryControlAssuranceRepository(session,tenant_id);self.members=MembershipRepository(session,tenant_id);self.model_client=model_client;self.response_model=response_model;self.correspondence_adapter=correspondence_adapter or SandboxSecureRegulatoryCorrespondenceAdapter()
    def _role(self,user_id,allowed,msg):
        m=self.members.get_by_user(user_id)
        if m is None or m.status!="active" or m.role not in allowed:raise ReviewConflictError(msg)
        return m
    def _reader(self,u):return self._role(u,self.READ_ROLES,"regulatory examination read role required")
    def _preparer(self,u):return self._role(u,self.PREPARER_ROLES,"authorized human regulatory response preparer required")
    def _checker(self,u):return self._role(u,self.CHECKER_ROLES,"authorized human regulatory response checker required")
    def _case(self,case_id,for_update=False):
        c=self.repo.case(case_id,for_update=for_update)
        if c is None:raise LookupError("regulatory examination case not found")
        return c
    def _supervisory_trace(self,supervisory_case_id,user_id):
        sup=RegulatorySupervisoryControlService(self.session,self.tenant_id)
        return sup.traceability(supervisory_case_id,user_id)
    def _source_bundle(self,supervisory_case_id,user_id):
        sc=self.super_repo.case(supervisory_case_id)
        if sc is None:raise LookupError("supervisory reconciliation case not found")
        certs=self.super_repo.certifications(supervisory_case_id)
        if not certs:raise ReviewConflictError("independent supervisory certification required before examination evidence management")
        trace=self._supervisory_trace(supervisory_case_id,user_id)
        package=self.control.package(sc.package_id)
        refs=[{"type":"supervisory_case","id":sc.case_id,"sha256":sc.source_snapshot_sha256},{"type":"supervisory_certification","id":certs[-1].certification_id,"sha256":certs[-1].certification_sha256},{"type":"transmission","id":sc.transmission_id,"sha256":trace.get("release49_release50",{}).get("release_sha256")},{"type":"certified_package","id":sc.package_id,"sha256":package.locked_manifest_sha256 if package else None}]
        refs=sorted(refs,key=lambda x:(x["type"],x["id"]))
        return sc,trace,package,refs,_sha({"refs":refs,"trace":trace})
    def open_inquiry(self,user_id,*,supervisory_case_id,external_inquiry_reference,inquiry_type,question_classification,inquiry_summary,response_due_at):
        self._preparer(user_id)
        if inquiry_type not in self.INQUIRY_TYPES:raise ReviewConflictError("unsupported regulator inquiry type")
        if question_classification not in self.QUESTION_CLASSES:raise ReviewConflictError("unsupported regulator question classification")
        existing=self.repo.case_by_external(external_inquiry_reference)
        if existing:return existing
        sc,trace,_,refs,watermark=self._source_bundle(supervisory_case_id,user_id)
        now=_now();due=_utc(response_due_at)
        if due<=now:raise ReviewConflictError("regulator response deadline must be in the future")
        row=self.repo.add(RegulatoryExaminationCaseModel(examination_case_id=f"rex_{uuid4().hex}",tenant_id=self.tenant_id,supervisory_case_id=sc.case_id,transmission_id=sc.transmission_id,package_id=sc.package_id,destination_id=sc.destination_id,external_inquiry_reference=external_inquiry_reference,inquiry_type=inquiry_type,question_classification=question_classification,inquiry_summary=inquiry_summary,status="open",severity="medium",source_watermark_sha256=watermark,source_refs=refs,case_version=1,assigned_preparer_user_id=user_id,response_due_at=due,follow_up_due_at=None,created_by_user_id=user_id,created_at=now,updated_at=now))
        self._audit(row,"examination.opened","human_regulatory_preparer",user_id,{"external_inquiry_reference":external_inquiry_reference,"question_classification":question_classification});self._emit("regulatory_examination.case.opened",row.examination_case_id,{"external_inquiry_reference":external_inquiry_reference,"due_at":due.isoformat()});return row
    def add_document_request(self,case_id,user_id,*,request_code,description,due_at,requested_refs):
        self._preparer(user_id);c=self._case(case_id,True)
        existing=next((x for x in self.repo.requests(case_id) if x.request_code==request_code),None)
        if existing:return existing
        row=self.repo.add(RegulatoryExaminationDocumentRequestModel(document_request_id=f"redr_{uuid4().hex}",tenant_id=self.tenant_id,examination_case_id=case_id,request_code=request_code,description=description,due_at=_utc(due_at),status="open",requested_refs=requested_refs,satisfied_refs=[],created_by_user_id=user_id,satisfied_by_user_id=None,created_at=_now(),satisfied_at=None));c.case_version+=1;c.updated_at=_now();self.session.flush();self._audit(c,"document_request.created","human_regulatory_preparer",user_id,{"document_request_id":row.document_request_id,"request_code":request_code});self._emit("regulatory_examination.document_request.created",case_id,{"request_code":request_code});return row
    def satisfy_document_request(self,case_id,request_code,user_id,*,satisfied_refs,expected_case_version):
        self._preparer(user_id);c=self._case(case_id,True)
        if c.case_version!=expected_case_version:raise ReviewConflictError("stale regulatory examination case version")
        req=next((x for x in self.repo.requests(case_id) if x.request_code==request_code),None)
        if req is None:raise LookupError("regulator document request not found")
        if not satisfied_refs:raise ReviewConflictError("satisfied evidence references required")
        req.status="satisfied";req.satisfied_refs=satisfied_refs;req.satisfied_by_user_id=user_id;req.satisfied_at=_now();c.case_version+=1;c.updated_at=_now();self.session.flush();self._audit(c,"document_request.satisfied","human_regulatory_preparer",user_id,{"request_code":request_code,"refs":satisfied_refs});return req
    def build_evidence_pack(self,case_id,user_id,*,expected_case_version):
        self._preparer(user_id);c=self._case(case_id,True)
        if c.case_version!=expected_case_version:raise ReviewConflictError("stale regulatory examination case version")
        sc,trace,package,refs,watermark=self._source_bundle(c.supervisory_case_id,user_id)
        requests=self.repo.requests(case_id);request_refs=[r for x in requests for r in x.satisfied_refs]
        evidence_refs=refs+request_refs
        citations=[{"citation_id":"supervisory-trace","source_type":"release51_supervisory_trace","source_id":c.supervisory_case_id,"sha256":sc.source_snapshot_sha256},{"citation_id":"certified-package","source_type":"release49_certified_package","source_id":c.package_id,"sha256":package.locked_manifest_sha256 if package else None},{"citation_id":"transport-ack","source_type":"release50_transport_ack","source_id":c.transmission_id,"sha256":_sha(trace.get("release49_release50",{}).get("acknowledgments",[]))}]
        citations += [{"citation_id":f"document-request-{i+1}","source_type":"regulator_requested_evidence","source_id":str(x.get("id") or x.get("evidence_id") or x.get("journal_id") or i+1),"sha256":x.get("sha256")} for i,x in enumerate(request_refs)]
        version=len(self.repo.packs(case_id))+1;payload={"case_id":case_id,"version":version,"source_watermark":watermark,"evidence_refs":evidence_refs,"citations":citations}
        row=self.repo.add(RegulatoryExaminationEvidencePackModel(evidence_pack_id=f"reep_{uuid4().hex}",tenant_id=self.tenant_id,examination_case_id=case_id,pack_version=version,evidence_refs=evidence_refs,citations=citations,source_watermark_sha256=watermark,payload_sha256=_sha(payload),created_by_user_id=user_id,locked_at=_now(),created_at=_now()));c.source_watermark_sha256=watermark;c.source_refs=refs;c.case_version+=1;c.updated_at=_now();self.session.flush();self._audit(c,"evidence_pack.locked","human_regulatory_preparer",user_id,{"evidence_pack_id":row.evidence_pack_id,"payload_sha256":row.payload_sha256});self._emit("regulatory_examination.evidence_pack.locked",case_id,{"evidence_pack_id":row.evidence_pack_id});return row
    def search_evidence(self,case_id,user_id,query,top_k=8):
        self._reader(user_id);c=self._case(case_id);packs=self.repo.packs(case_id)
        if not packs:raise ReviewConflictError("locked examination evidence pack required before cited retrieval")
        pack=packs[-1];sup=self._supervisory_trace(c.supervisory_case_id,user_id);package=self.control.package(c.package_id)
        docs=[("certified_filing",package.manifest if package else {},{"source_type":"release49_package_manifest","source_id":c.package_id,"sha256":package.locked_manifest_sha256 if package else None}),("transport_and_ack",sup.get("release49_release50",{}),{"source_type":"release50_transport","source_id":c.transmission_id,"sha256":_sha(sup.get("release49_release50",{}))}),("supervisory_control",sup,{"source_type":"release51_supervisory_certification","source_id":c.supervisory_case_id,"sha256":c.source_watermark_sha256}),("examination_pack",{"evidence_refs":pack.evidence_refs,"citations":pack.citations},{"source_type":"release52_evidence_pack","source_id":pack.evidence_pack_id,"sha256":pack.payload_sha256})]
        terms=[t for t in query.lower().split() if len(t)>1];out=[]
        for scope,payload,cite in docs:
            text=_canon(payload);lower=text.lower();score=sum(lower.count(t) for t in terms)
            if score or not out:out.append({"scope":scope,"score":score,"excerpt":text[:1600],"citation":cite})
        out=sorted(out,key=lambda x:(-x["score"],x["scope"]))[:top_k]
        return {"query":query,"results":out,"evidence_pack_id":pack.evidence_pack_id,"citation_required":True,"financial_accounting_sources_read_only":True,"authority":REGULATORY_EXAMINATION_AUTHORITY}
    def draft_response(self,case_id,user_id,*,response_text,cited_refs,use_ai_assistance,idempotency_key,expected_case_version):
        self._preparer(user_id);c=self._case(case_id,True)
        if c.case_version!=expected_case_version:raise ReviewConflictError("stale regulatory examination case version")
        existing=self.session.scalar(select(RegulatoryExaminationResponseModel).where(RegulatoryExaminationResponseModel.tenant_id==self.tenant_id,RegulatoryExaminationResponseModel.idempotency_key==idempotency_key))
        if existing:return existing
        packs=self.repo.packs(case_id)
        if not packs:raise ReviewConflictError("locked examination evidence pack required before response drafting")
        pack=packs[-1]
        if not cited_refs:cited_refs=pack.citations[:3]
        valid_ids={x.get("citation_id") for x in pack.citations};supplied={x.get("citation_id") for x in cited_refs if x.get("citation_id")}
        if supplied and not supplied.issubset(valid_ids):raise ReviewConflictError("response citations must belong to the locked examination evidence pack")
        ai_meta={"authority":"none","approval_required":True,"mode":"human_authored"}
        text=(response_text or "").strip()
        if use_ai_assistance:
            evidence=self.search_evidence(case_id,user_id,c.inquiry_summary,top_k=6)
            if self.model_client is not None:
                resp=self.model_client.generate(model=self.response_model,instructions="Draft a concise regulatory examination response using only supplied evidence. Never claim approval authority. Return citations exactly from the supplied evidence and state uncertainties.",input_text=_canon({"inquiry":c.inquiry_summary,"evidence":evidence["results"]}),schema=AIResponseDraft)
                parsed=resp.parsed;text=parsed.response_text;cited_refs=parsed.cited_refs;ai_meta={"authority":"none","approval_required":True,"mode":"openai_responses_structured","model":resp.model,"response_id":resp.response_id}
            else:
                if not text:text=f"Draft response for regulator inquiry {c.external_inquiry_reference}: the certified filing, transmission acknowledgment, and supervisory evidence have been assembled for human review. Evidence citations are attached; any conclusion remains subject to independent human approval."
                ai_meta={"authority":"none","approval_required":True,"mode":"deterministic_guarded_fallback"}
        if len(text)<20:raise ReviewConflictError("substantive human-reviewable response draft required")
        responses=self.repo.responses(case_id);prev=responses[-1].response_sha256 if responses else None;version=len(responses)+1;payload={"case_id":case_id,"pack":pack.payload_sha256,"version":version,"text":text,"citations":cited_refs,"previous":prev}
        row=self.repo.add(RegulatoryExaminationResponseModel(response_id=f"rer_{uuid4().hex}",tenant_id=self.tenant_id,examination_case_id=case_id,evidence_pack_id=pack.evidence_pack_id,response_version=version,status="draft",response_text=text,cited_refs=cited_refs,ai_assisted=use_ai_assistance,ai_metadata=ai_meta,prepared_by_user_id=user_id,approved_by_user_id=None,approval_rationale=None,previous_response_sha256=prev,response_sha256=_sha(payload),idempotency_key=idempotency_key,created_at=_now(),approved_at=None,sent_at=None));c.assigned_preparer_user_id=user_id;c.status="response_drafting";c.case_version+=1;c.updated_at=_now();self.session.flush();self._audit(c,"response.drafted","human_regulatory_preparer",user_id,{"response_id":row.response_id,"ai_assisted":use_ai_assistance,"authority":"none"});self._emit("regulatory_examination.response.drafted",case_id,{"response_id":row.response_id,"ai_assisted":use_ai_assistance});return row
    def approve_response(self,case_id,response_id,user_id,*,approval_rationale,expected_case_version):
        self._checker(user_id);c=self._case(case_id,True)
        if c.case_version!=expected_case_version:raise ReviewConflictError("stale regulatory examination case version")
        r=self.repo.response(response_id)
        if r is None or r.examination_case_id!=case_id:raise LookupError("regulatory response draft not found")
        if r.prepared_by_user_id==user_id:raise ReviewConflictError("response maker and checker must be different humans")
        if r.status!="draft":raise ReviewConflictError("only draft examination responses may be approved")
        if not r.cited_refs:raise ReviewConflictError("cited evidence required before examination response approval")
        r.status="approved";r.approved_by_user_id=user_id;r.approval_rationale=approval_rationale;r.approved_at=_now();c.status="response_approved";c.case_version+=1;c.updated_at=_now();self.session.flush();self._audit(c,"response.approved","human_regulatory_checker",user_id,{"response_id":r.response_id,"maker":r.prepared_by_user_id});self._emit("regulatory_examination.response.approved",case_id,{"response_id":r.response_id});return r
    def deliver_response(self,case_id,response_id,user_id,*,channel,subject,external_reference,supplemental_submission_reference,idempotency_key,expected_case_version):
        self._checker(user_id);c=self._case(case_id,True)
        if c.case_version!=expected_case_version:raise ReviewConflictError("stale regulatory examination case version")
        r=self.repo.response(response_id)
        if r is None or r.examination_case_id!=case_id:raise LookupError("regulatory response not found")
        if r.status not in {"approved","sent"}:raise ReviewConflictError("independently approved examination response required before secure delivery")
        if channel not in self.SECURE_CHANNELS:raise ReviewConflictError("unsupported secure regulator correspondence channel")
        existing=self.session.scalar(select(RegulatoryExaminationCorrespondenceModel).where(RegulatoryExaminationCorrespondenceModel.tenant_id==self.tenant_id,RegulatoryExaminationCorrespondenceModel.idempotency_key==idempotency_key))
        if existing:return existing
        delivery=self.correspondence_adapter.deliver(channel=channel,subject=subject,body=r.response_text,idempotency_key=idempotency_key)
        external_reference=external_reference or delivery.external_reference
        payload={"response_sha256":r.response_sha256,"channel":channel,"subject":subject,"external_reference":external_reference,"supplemental_submission_reference":supplemental_submission_reference,"delivery_status":delivery.status,"provider_metadata":delivery.provider_metadata}
        corr=self.repo.add(RegulatoryExaminationCorrespondenceModel(correspondence_id=f"rec_{uuid4().hex}",tenant_id=self.tenant_id,examination_case_id=case_id,response_id=response_id,direction="outbound",channel=channel,subject=subject,body=r.response_text,external_reference=external_reference,supplemental_submission_reference=supplemental_submission_reference,delivered=True,actor_user_id=user_id,payload_sha256=_sha(payload),idempotency_key=idempotency_key,created_at=_now()));r.status="sent";r.sent_at=_now();c.status="awaiting_regulator_follow_up";c.case_version+=1;c.updated_at=_now();self.session.flush();self._audit(c,"response.delivered","human_regulatory_checker",user_id,{"response_id":response_id,"channel":channel,"supplemental_submission_reference":supplemental_submission_reference});self._emit("regulatory_examination.response.delivered",case_id,{"response_id":response_id,"channel":channel});return corr
    def record_finding(self,case_id,user_id,*,finding_code,severity,material,description,source_refs):
        self._preparer(user_id);c=self._case(case_id,True)
        if severity not in self.FINDING_SEVERITIES:raise ReviewConflictError("unsupported examination finding severity")
        existing=next((x for x in self.repo.findings(case_id) if x.finding_code==finding_code),None)
        if existing:return existing
        row=self.repo.add(RegulatoryExaminationFindingModel(finding_id=f"ref_{uuid4().hex}",tenant_id=self.tenant_id,examination_case_id=case_id,finding_code=finding_code,severity=severity,material=material,description=description,status="open",source_refs=source_refs,created_by_user_id=user_id,created_at=_now(),resolved_by_user_id=None,resolved_at=None));c.status="finding_open" if material else c.status;c.case_version+=1;c.updated_at=_now();self.session.flush();self._audit(c,"finding.recorded","human_regulatory_preparer",user_id,{"finding_code":finding_code,"material":material});self._emit("regulatory_examination.finding.recorded",case_id,{"finding_code":finding_code,"material":material});return row
    def resolve_finding(self,case_id,finding_code,user_id,*,rationale,expected_case_version):
        self._checker(user_id);c=self._case(case_id,True)
        if c.case_version!=expected_case_version:raise ReviewConflictError("stale regulatory examination case version")
        f=next((x for x in self.repo.findings(case_id) if x.finding_code==finding_code),None)
        if f is None:raise LookupError("examination finding not found")
        if f.material:raise ReviewConflictError("material examination findings require Release 53 governed corrective-action closure certification")
        f.status="resolved";f.resolved_by_user_id=user_id;f.resolved_at=_now();c.case_version+=1;c.updated_at=_now();self.session.flush();self._audit(c,"finding.resolved","human_regulatory_checker",user_id,{"finding_code":finding_code,"rationale":rationale});return f
    def add_commitment(self,case_id,user_id,*,commitment_key,description,due_at,owner_user_id,evidence_refs):
        self._checker(user_id);c=self._case(case_id,True);self._role(owner_user_id,self.PREPARER_ROLES,"active human commitment owner required")
        existing=next((x for x in self.repo.commitments(case_id) if x.commitment_key==commitment_key),None)
        if existing:return existing
        row=self.repo.add(RegulatoryRemediationCommitmentModel(commitment_id=f"rcm_{uuid4().hex}",tenant_id=self.tenant_id,examination_case_id=case_id,commitment_key=commitment_key,description=description,due_at=_utc(due_at),status="open",owner_user_id=owner_user_id,evidence_refs=evidence_refs,created_at=_now(),completed_at=None));c.follow_up_due_at=_utc(due_at);c.status="remediation_commitment_open";c.case_version+=1;c.updated_at=_now();self.session.flush();self._audit(c,"remediation.commitment.created","human_regulatory_checker",user_id,{"commitment_id":row.commitment_id,"owner":owner_user_id});return row
    def complete_commitment(self,case_id,commitment_key,user_id,*,evidence_refs,expected_case_version):
        self._preparer(user_id);c=self._case(case_id,True)
        if c.case_version!=expected_case_version:raise ReviewConflictError("stale regulatory examination case version")
        row=next((x for x in self.repo.commitments(case_id) if x.commitment_key==commitment_key),None)
        if row is None:raise LookupError("remediation commitment not found")
        if row.owner_user_id!=user_id and self.members.get_by_user(user_id).role not in self.CHECKER_ROLES:raise ReviewConflictError("commitment owner or authorized supervisor required")
        if not evidence_refs:raise ReviewConflictError("remediation completion evidence required")
        row.status="completed";row.evidence_refs=evidence_refs;row.completed_at=_now();c.case_version+=1;c.updated_at=_now();self.session.flush();self._audit(c,"remediation.commitment.completed","human_regulatory_preparer",user_id,{"commitment_key":commitment_key,"evidence_refs":evidence_refs});return row
    def refresh_operations(self,actor_id="regulatory-examination-worker",actor_type="monitoring_worker"):
        now=_now();updated=0
        for c in self.repo.cases():
            overdue=bool(c.response_due_at and _utc(c.response_due_at)<now and c.status not in {"closed"})
            follow=bool(c.follow_up_due_at and _utc(c.follow_up_due_at)<now and any(x.status=="open" for x in self.repo.commitments(c.examination_case_id)))
            if (overdue or follow) and c.severity!="high":
                c.severity="high";c.updated_at=now;updated+=1;self._audit(c,"supervisory.escalation.raised",actor_type,actor_id,{"response_overdue":overdue,"follow_up_overdue":follow});self._emit("regulatory_examination.supervisory.escalated",c.examination_case_id,{"response_overdue":overdue,"follow_up_overdue":follow})
        record_regulatory_examination(metric="operational_escalations",value=updated,attributes={"tenant_id":self.tenant_id});return updated
    def close_examination(self,case_id,user_id,*,closure_rationale,expected_case_version):
        self._checker(user_id);c=self._case(case_id,True)
        if c.case_version!=expected_case_version:raise ReviewConflictError("stale regulatory examination case version")
        if any(x.status=="open" for x in self.repo.requests(case_id)):raise ReviewConflictError("open regulator document requests block examination closure")
        if any(x.status=="open" and x.material for x in self.repo.findings(case_id)):raise ReviewConflictError("open material examination findings block closure")
        if any(x.status=="open" for x in self.repo.commitments(case_id)):raise ReviewConflictError("open remediation commitments block examination closure")
        responses=self.repo.responses(case_id)
        if not responses or responses[-1].status!="sent":raise ReviewConflictError("human-approved regulator response delivery required before examination closure")
        c.status="closed";c.case_version+=1;c.updated_at=_now();self.session.flush();self._audit(c,"examination.closed","human_regulatory_checker",user_id,{"closure_rationale":closure_rationale});self._emit("regulatory_examination.case.closed",case_id,{"closed_by":user_id});return c
    def dashboard(self,user_id):
        self._reader(user_id);self.refresh_operations(actor_id="dashboard-refresh",actor_type="derived_monitoring");now=_now();cases=self.repo.cases();views=[]
        for c in cases:
            age=max(0,(now-_utc(c.created_at)).days);views.append({**self._case_view(c),"aging_bucket":"0-2d" if age<=2 else "3-7d" if age<=7 else "8-30d" if age<=30 else "31+d","open_document_requests":sum(x.status=="open" for x in self.repo.requests(c.examination_case_id)),"open_material_findings":sum(x.status=="open" and x.material for x in self.repo.findings(c.examination_case_id)),"open_commitments":sum(x.status=="open" for x in self.repo.commitments(c.examination_case_id))})
        return {"authority":REGULATORY_EXAMINATION_AUTHORITY,"kpis":{"cases":len(cases),"open_cases":sum(x.status!="closed" for x in cases),"overdue":sum(_utc(x.response_due_at)<now and x.status!="closed" for x in cases),"closed":sum(x.status=="closed" for x in cases)},"cases":views}
    def traceability(self,case_id,user_id):
        self._reader(user_id);c=self._case(case_id);sup=self._supervisory_trace(c.supervisory_case_id,user_id)
        return {"case":self._case_view(c),"certified_filing_to_supervision":sup,"document_requests":[{"request_code":x.request_code,"status":x.status,"due_at":x.due_at,"satisfied_refs":x.satisfied_refs} for x in self.repo.requests(case_id)],"evidence_packs":[{"evidence_pack_id":x.evidence_pack_id,"version":x.pack_version,"payload_sha256":x.payload_sha256,"source_watermark_sha256":x.source_watermark_sha256,"citations":x.citations} for x in self.repo.packs(case_id)],"responses":[{"response_id":x.response_id,"version":x.response_version,"status":x.status,"ai_assisted":x.ai_assisted,"authority":"none","prepared_by":x.prepared_by_user_id,"approved_by":x.approved_by_user_id,"response_sha256":x.response_sha256,"previous_response_sha256":x.previous_response_sha256} for x in self.repo.responses(case_id)],"correspondence":[{"correspondence_id":x.correspondence_id,"channel":x.channel,"external_reference":x.external_reference,"supplemental_submission_reference":x.supplemental_submission_reference,"payload_sha256":x.payload_sha256} for x in self.repo.correspondence(case_id)],"findings":[{"finding_code":x.finding_code,"material":x.material,"status":x.status,"source_refs":x.source_refs} for x in self.repo.findings(case_id)],"commitments":[{"commitment_key":x.commitment_key,"status":x.status,"due_at":x.due_at,"evidence_refs":x.evidence_refs} for x in self.repo.commitments(case_id)],"audit_chain":[{"sequence":x.sequence,"event_type":x.event_type,"event_sha256":x.event_sha256,"previous_event_sha256":x.previous_event_sha256} for x in self.repo.audit(case_id)],"provenance":"Release 49 certified filing -> Release 50 human release/transmission/cryptographic ACK -> Release 51 supervisory certification -> Release 52 regulator inquiry -> immutable evidence pack -> cited retrieval -> AI-assisted draft -> human maker/checker approval -> secure correspondence -> findings/remediation -> human examination closure","authority":REGULATORY_EXAMINATION_AUTHORITY}
    def audit_export(self,case_id,user_id):
        trace=self.traceability(case_id,user_id);manifest={"export_type":"regulatory_examination_inquiry_response_audit","case_id":case_id,"generated_at":_now().isoformat(),"traceability":trace};return {"manifest":manifest,"manifest_sha256":_sha(manifest),"immutable_source":True,"financial_accounting_mutation_authority":False,"human_response_approval_required":True}
    def _case_view(self,c):return {"examination_case_id":c.examination_case_id,"supervisory_case_id":c.supervisory_case_id,"transmission_id":c.transmission_id,"package_id":c.package_id,"external_inquiry_reference":c.external_inquiry_reference,"inquiry_type":c.inquiry_type,"question_classification":c.question_classification,"inquiry_summary":c.inquiry_summary,"status":c.status,"severity":c.severity,"case_version":c.case_version,"source_watermark_sha256":c.source_watermark_sha256,"response_due_at":c.response_due_at,"follow_up_due_at":c.follow_up_due_at,"updated_at":c.updated_at}
    def _audit(self,c,event_type,actor_type,actor_id,details):
        chain=self.repo.audit(c.examination_case_id);seq=len(chain)+1;prev=chain[-1].event_sha256 if chain else None;payload={"case_id":c.examination_case_id,"sequence":seq,"event_type":event_type,"actor_type":actor_type,"actor_id":actor_id,"details":details,"previous":prev};self.repo.add(RegulatoryExaminationAuditEventModel(audit_event_id=f"reau_{uuid4().hex}",tenant_id=self.tenant_id,examination_case_id=c.examination_case_id,sequence=seq,event_type=event_type,actor_type=actor_type,actor_id=actor_id,details=details,previous_event_sha256=prev,event_sha256=_sha(payload),occurred_at=_now()))
    def _emit(self,event_type,aggregate_id,payload):enqueue_realtime_event(self.session,envelope=EventEnvelope(event_id=f"rt_{uuid4().hex}",event_type=event_type,tenant_id=self.tenant_id,claim_id=None,aggregate_type="regulatory_examination",aggregate_id=str(aggregate_id),occurred_at=_now(),producer="medclaimiq-regulatory-examination",payload=payload,metadata={"human_response_approval_required":True,"ai_authority":"draft_and_recommendation_only","financial_accounting_mutation_authority":False,"fund_movement":False}),topic=EventTopic.CLAIMS.value)
