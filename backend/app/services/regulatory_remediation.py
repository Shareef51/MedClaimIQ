from __future__ import annotations
import hashlib, json
from datetime import UTC, datetime
from uuid import uuid4
from sqlalchemy.orm import Session
from app.agents.model_client import StructuredModelClient
from app.domain.realtime import EventEnvelope, EventTopic
from app.domain.regulatory_remediation import REGULATORY_REMEDIATION_AUTHORITY
from app.models.regulatory_remediation import *
from app.observability.metrics import record_regulatory_remediation
from app.realtime.events import enqueue_realtime_event
from app.repositories.regulatory_examination import RegulatoryExaminationRepository
from app.repositories.regulatory_remediation import RegulatoryRemediationRepository
from app.repositories.tenancy import MembershipRepository
from app.schemas.regulatory_remediation import AIRegulatoryRemediationRecommendation
from app.services.review_workbench import ReviewConflictError

def _now(): return datetime.now(UTC)
def _canon(v): return json.dumps(v,sort_keys=True,separators=(",",":"),default=str)
def _sha(v): return hashlib.sha256((v if isinstance(v,str) else _canon(v)).encode()).hexdigest()
def _utc(v):
    if v is None:return None
    return v.replace(tzinfo=UTC) if v.tzinfo is None else v.astimezone(UTC)

class RegulatoryRemediationService:
    READ_ROLES={"auditor","tenant_admin","accounting_controller"}
    PREPARER_ROLES={"auditor","tenant_admin","accounting_controller"}
    APPROVER_ROLES={"auditor","tenant_admin"}
    TASK_TYPES={"corrective","preventive","control_redesign","data_correction","training","process","monitoring"}
    CHECKPOINT_TYPES={"implementation_evidence","financial_impact","accounting_impact","control_redesign","regulator_followup"}
    RETEST_OUTCOMES={"pass","fail","partial"}
    WAIVER_TYPES={"temporary_exception","deadline_extension","control_exception"}
    CLOSURE_CONCLUSIONS={"effective","ineffective","partially_effective"}
    def __init__(self,session:Session,tenant_id:str,*,model_client:StructuredModelClient|None=None,recommendation_model:str="gpt-5.6-terra"):
        self.session=session;self.tenant_id=tenant_id;self.repo=RegulatoryRemediationRepository(session,tenant_id);self.exam=RegulatoryExaminationRepository(session,tenant_id);self.members=MembershipRepository(session,tenant_id);self.model_client=model_client;self.recommendation_model=recommendation_model
    def _role(self,user_id,allowed,msg):
        m=self.members.get_by_user(user_id)
        if m is None or m.status!="active" or m.role not in allowed:raise ReviewConflictError(msg)
        return m
    def _reader(self,u):return self._role(u,self.READ_ROLES,"regulatory remediation read role required")
    def _preparer(self,u):return self._role(u,self.PREPARER_ROLES,"authorized human remediation preparer required")
    def _approver(self,u):return self._role(u,self.APPROVER_ROLES,"authorized human remediation approver required")
    def _plan(self,plan_id,for_update=False):
        p=self.repo.plan(plan_id,for_update=for_update)
        if p is None:raise LookupError("regulatory remediation plan not found")
        return p
    def _finding(self,case_id,finding_code):
        row=next((x for x in self.exam.findings(case_id) if x.finding_code==finding_code),None)
        if row is None:raise LookupError("regulatory examination finding not found")
        return row
    def _risk(self,finding,financial,accounting):
        base={"low":20,"medium":40,"high":65,"critical":85}.get(finding.severity,40)
        if finding.material:base+=10
        if "no impact" not in financial.lower():base+=3
        if "no impact" not in accounting.lower():base+=2
        score=min(100,base);level="critical" if score>=85 else "high" if score>=65 else "medium" if score>=40 else "low"
        return score,level
    def create_plan(self,case_id,user_id,*,finding_code,root_cause,corrective_action_summary,preventive_action_summary,control_redesign_proposal,financial_impact_analysis,accounting_impact_analysis,owner_user_id,due_at,use_ai_assistance=False):
        self._preparer(user_id);self._preparer(owner_user_id)
        case=self.exam.case(case_id)
        if case is None:raise LookupError("regulatory examination case not found")
        finding=self._finding(case_id,finding_code)
        existing=self.repo.plans_for_finding(finding.finding_id);version=len(existing)+1;prev=existing[-1].plan_sha256 if existing else None
        score,level=self._risk(finding,financial_impact_analysis,accounting_impact_analysis)
        ai={"authority":"none","approval_required":True,"mode":"human_authored"}
        if use_ai_assistance:
            ai={"authority":"none","approval_required":True,"mode":"deterministic_guarded_fallback","recommendation":"Prioritize root-cause removal, preventive controls, independent retesting, and evidence-bound closure."}
            if self.model_client is not None:
                resp=self.model_client.generate(model=self.recommendation_model,instructions="Recommend regulatory remediation using only the supplied finding and impact analysis. Never approve remediation, never alter financial/accounting records, and never claim regulatory authority.",input_text=_canon({"finding":finding.description,"root_cause":root_cause,"financial_impact":financial_impact_analysis,"accounting_impact":accounting_impact_analysis}),schema=AIRegulatoryRemediationRecommendation)
                parsed=resp.parsed;ai={"authority":"none","approval_required":True,"mode":"openai_responses_structured","model":resp.model,"response_id":resp.response_id,**parsed.model_dump()}
        due=_utc(due_at)
        if due<=_now():raise ReviewConflictError("remediation due date must be in the future")
        payload={"case_id":case_id,"finding_id":finding.finding_id,"version":version,"root_cause":root_cause,"corrective":corrective_action_summary,"preventive":preventive_action_summary,"redesign":control_redesign_proposal,"financial":financial_impact_analysis,"accounting":accounting_impact_analysis,"risk_score":score,"owner":owner_user_id,"previous":prev}
        row=self.repo.add(RegulatoryRemediationPlanModel(plan_id=f"rrp_{uuid4().hex}",tenant_id=self.tenant_id,examination_case_id=case_id,finding_id=finding.finding_id,finding_code=finding.finding_code,plan_version=version,status="draft",root_cause=root_cause,corrective_action_summary=corrective_action_summary,preventive_action_summary=preventive_action_summary,control_redesign_proposal=control_redesign_proposal,financial_impact_analysis=financial_impact_analysis,accounting_impact_analysis=accounting_impact_analysis,risk_score=score,risk_level=level,ai_assisted=use_ai_assistance,ai_recommendation=ai,ai_authority="none",owner_user_id=owner_user_id,prepared_by_user_id=user_id,approved_by_user_id=None,approval_rationale=None,previous_plan_sha256=prev,plan_sha256=_sha(payload),due_at=due,created_at=_now(),approved_at=None,updated_at=_now()))
        finding.status="remediation_program_open";self.session.flush();self._audit(row,"plan.created","human_remediation_preparer",user_id,{"finding_code":finding_code,"risk_score":score,"ai_authority":"none"});self._emit("regulatory_remediation.plan.created",row.plan_id,{"finding_code":finding_code,"risk_level":level});return row
    def approve_plan(self,plan_id,user_id,*,approval_rationale):
        self._approver(user_id);p=self._plan(plan_id,True)
        if p.status!="draft":raise ReviewConflictError("only draft remediation plans may be approved")
        if user_id in {p.prepared_by_user_id,p.owner_user_id}:raise ReviewConflictError("remediation maker/owner and approver must be different humans")
        p.status="approved";p.approved_by_user_id=user_id;p.approval_rationale=approval_rationale;p.approved_at=_now();p.updated_at=_now();self.session.flush();self._audit(p,"plan.approved","human_remediation_approver",user_id,{"maker":p.prepared_by_user_id,"owner":p.owner_user_id});self._emit("regulatory_remediation.plan.approved",p.plan_id,{"approved_by":user_id});return p
    def add_task(self,plan_id,user_id,*,task_key,task_type,description,owner_user_id,dependency_keys,due_at):
        self._preparer(user_id);self._preparer(owner_user_id);p=self._plan(plan_id,True)
        if task_type not in self.TASK_TYPES:raise ReviewConflictError("unsupported corrective/preventive task type")
        existing=self.repo.task(plan_id,task_key)
        if existing:return existing
        known={x.task_key for x in self.repo.tasks(plan_id)}
        if not set(dependency_keys).issubset(known):raise ReviewConflictError("task dependencies must already exist in this remediation plan")
        row=self.repo.add(RegulatoryRemediationTaskModel(task_id=f"rrt_{uuid4().hex}",tenant_id=self.tenant_id,plan_id=plan_id,task_key=task_key,task_type=task_type,description=description,owner_user_id=owner_user_id,dependency_keys=dependency_keys,status="open",due_at=_utc(due_at),evidence_refs=[],created_at=_now(),completed_at=None));p.updated_at=_now();self.session.flush();self._audit(p,"task.created","human_remediation_preparer",user_id,{"task_key":task_key,"dependencies":dependency_keys});return row
    def complete_task(self,plan_id,task_key,user_id,*,evidence_refs):
        self._preparer(user_id);p=self._plan(plan_id,True);t=self.repo.task(plan_id,task_key)
        if t is None:raise LookupError("remediation task not found")
        if t.owner_user_id!=user_id and self.members.get_by_user(user_id).role not in self.APPROVER_ROLES:raise ReviewConflictError("task owner or authorized supervisor required")
        if not evidence_refs:raise ReviewConflictError("implementation evidence required before corrective task completion")
        tasks={x.task_key:x for x in self.repo.tasks(plan_id)}
        if any(tasks[k].status!="completed" for k in t.dependency_keys):raise ReviewConflictError("remediation task dependencies must be completed first")
        t.status="completed";t.evidence_refs=evidence_refs;t.completed_at=_now();p.updated_at=_now();self.session.flush();self._audit(p,"task.completed","human_remediation_owner",user_id,{"task_key":task_key,"evidence_refs":evidence_refs});self._emit("regulatory_remediation.task.completed",p.plan_id,{"task_key":task_key});return t
    def lock_checkpoint(self,plan_id,user_id,*,checkpoint_key,checkpoint_type,evidence_refs):
        self._preparer(user_id);p=self._plan(plan_id,True)
        if checkpoint_type not in self.CHECKPOINT_TYPES:raise ReviewConflictError("unsupported remediation checkpoint type")
        if not evidence_refs:raise ReviewConflictError("evidence-bound remediation checkpoint requires evidence")
        existing=next((x for x in self.repo.checkpoints(plan_id) if x.checkpoint_key==checkpoint_key),None)
        if existing:return existing
        watermark=_sha(sorted(evidence_refs,key=lambda x:_canon(x)));payload={"plan":p.plan_sha256,"checkpoint_key":checkpoint_key,"type":checkpoint_type,"evidence":evidence_refs,"watermark":watermark}
        row=self.repo.add(RegulatoryRemediationCheckpointModel(checkpoint_id=f"rrc_{uuid4().hex}",tenant_id=self.tenant_id,plan_id=plan_id,checkpoint_key=checkpoint_key,checkpoint_type=checkpoint_type,evidence_refs=evidence_refs,source_watermark_sha256=watermark,payload_sha256=_sha(payload),created_by_user_id=user_id,locked_at=_now()));p.updated_at=_now();self.session.flush();self._audit(p,"checkpoint.locked","human_remediation_owner",user_id,{"checkpoint_key":checkpoint_key,"type":checkpoint_type,"payload_sha256":row.payload_sha256});return row
    def retest_control(self,plan_id,user_id,*,control_key,methodology,expected_result,observed_result,outcome,evidence_refs):
        self._approver(user_id);p=self._plan(plan_id,True)
        if p.status not in {"approved","retesting"}:raise ReviewConflictError("approved remediation plan required before control retesting")
        if user_id in {p.prepared_by_user_id,p.owner_user_id}:raise ReviewConflictError("control retester must be independent of remediation maker/owner")
        if outcome not in self.RETEST_OUTCOMES:raise ReviewConflictError("unsupported control retest outcome")
        if not evidence_refs:raise ReviewConflictError("control retest evidence required")
        seq=sum(x.control_key==control_key for x in self.repo.retests(plan_id))+1;payload={"plan":p.plan_sha256,"control_key":control_key,"sequence":seq,"methodology":methodology,"expected":expected_result,"observed":observed_result,"outcome":outcome,"evidence":evidence_refs,"retester":user_id}
        row=self.repo.add(RegulatoryControlRetestModel(retest_id=f"rrx_{uuid4().hex}",tenant_id=self.tenant_id,plan_id=plan_id,control_key=control_key,retest_sequence=seq,methodology=methodology,expected_result=expected_result,observed_result=observed_result,outcome=outcome,evidence_refs=evidence_refs,retested_by_user_id=user_id,payload_sha256=_sha(payload),retested_at=_now()));p.status="retesting";p.updated_at=_now();self.session.flush();self._audit(p,"control.retested","human_independent_retester",user_id,{"control_key":control_key,"outcome":outcome});self._emit("regulatory_remediation.control.retested",p.plan_id,{"control_key":control_key,"outcome":outcome});return row
    def request_waiver(self,plan_id,user_id,*,waiver_key,waiver_type,rationale,risk_acceptance,expires_at=None):
        self._preparer(user_id);p=self._plan(plan_id,True)
        if waiver_type not in self.WAIVER_TYPES:raise ReviewConflictError("unsupported remediation waiver type")
        existing=self.repo.waiver(plan_id,waiver_key)
        if existing:return existing
        row=self.repo.add(RegulatoryRemediationWaiverModel(waiver_id=f"rrw_{uuid4().hex}",tenant_id=self.tenant_id,plan_id=plan_id,waiver_key=waiver_key,waiver_type=waiver_type,rationale=rationale,risk_acceptance=risk_acceptance,status="pending",requested_by_user_id=user_id,decided_by_user_id=None,decision_rationale=None,expires_at=_utc(expires_at),created_at=_now(),decided_at=None));p.updated_at=_now();self.session.flush();self._audit(p,"waiver.requested","human_remediation_preparer",user_id,{"waiver_key":waiver_key});return row
    def decide_waiver(self,plan_id,waiver_key,user_id,*,approve,decision_rationale):
        self._approver(user_id);p=self._plan(plan_id,True);w=self.repo.waiver(plan_id,waiver_key)
        if w is None:raise LookupError("remediation waiver not found")
        if w.requested_by_user_id==user_id:raise ReviewConflictError("waiver requester and approver must be different humans")
        if w.status!="pending":raise ReviewConflictError("only pending remediation waivers may be decided")
        w.status="approved" if approve else "rejected";w.decided_by_user_id=user_id;w.decision_rationale=decision_rationale;w.decided_at=_now();p.updated_at=_now();self.session.flush();self._audit(p,"waiver.decided","human_remediation_approver",user_id,{"waiver_key":waiver_key,"status":w.status});return w
    def draft_followup(self,plan_id,user_id,*,response_text,cited_refs):
        self._preparer(user_id);p=self._plan(plan_id,True)
        if not cited_refs:raise ReviewConflictError("regulator follow-up response requires remediation evidence citations")
        rows=self.repo.followups(plan_id);version=len(rows)+1;prev=rows[-1].response_sha256 if rows else None;payload={"plan":p.plan_sha256,"version":version,"text":response_text,"citations":cited_refs,"previous":prev}
        row=self.repo.add(RegulatoryRemediationFollowupModel(followup_id=f"rrf_{uuid4().hex}",tenant_id=self.tenant_id,plan_id=plan_id,response_version=version,status="draft",response_text=response_text,cited_refs=cited_refs,prepared_by_user_id=user_id,approved_by_user_id=None,previous_response_sha256=prev,response_sha256=_sha(payload),approval_rationale=None,created_at=_now(),approved_at=None));p.updated_at=_now();self.session.flush();self._audit(p,"followup.drafted","human_remediation_preparer",user_id,{"followup_id":row.followup_id,"version":version});return row
    def approve_followup(self,plan_id,followup_id,user_id,*,approval_rationale):
        self._approver(user_id);p=self._plan(plan_id,True);row=next((x for x in self.repo.followups(plan_id) if x.followup_id==followup_id),None)
        if row is None:raise LookupError("regulator follow-up response not found")
        if row.prepared_by_user_id==user_id:raise ReviewConflictError("follow-up response maker and checker must be different humans")
        if row.status!="draft":raise ReviewConflictError("only draft follow-up responses may be approved")
        row.status="approved";row.approved_by_user_id=user_id;row.approval_rationale=approval_rationale;row.approved_at=_now();p.updated_at=_now();self.session.flush();self._audit(p,"followup.approved","human_regulatory_checker",user_id,{"followup_id":followup_id});return row
    def certify_closure(self,plan_id,user_id,*,conclusion,closure_rationale):
        self._approver(user_id);p=self._plan(plan_id,True)
        if conclusion not in self.CLOSURE_CONCLUSIONS:raise ReviewConflictError("unsupported remediation effectiveness conclusion")
        if user_id in {p.prepared_by_user_id,p.owner_user_id,p.approved_by_user_id}:raise ReviewConflictError("final remediation closure certifier must be independent of maker, owner, and plan approver")
        if p.status not in {"approved","retesting","closure_ready"}:raise ReviewConflictError("approved remediation plan required before closure certification")
        tasks=self.repo.tasks(plan_id)
        if not tasks or any(x.status!="completed" for x in tasks):raise ReviewConflictError("all corrective/preventive action tasks must be completed before closure certification")
        checkpoints=self.repo.checkpoints(plan_id)
        if not any(x.checkpoint_type=="implementation_evidence" for x in checkpoints):raise ReviewConflictError("immutable implementation evidence checkpoint required before closure certification")
        retests=self.repo.retests(plan_id)
        if not retests or any(x.outcome!="pass" for x in retests):raise ReviewConflictError("passing independent control retest required before effective remediation closure")
        waivers=self.repo.waivers(plan_id);now=_now()
        if any(x.status in {"pending","approved"} and (x.expires_at is None or _utc(x.expires_at)>now) for x in waivers):raise ReviewConflictError("open remediation waiver/exception blocks final closure certification")
        followups=self.repo.followups(plan_id)
        if not followups or followups[-1].status!="approved":raise ReviewConflictError("independently approved regulator follow-up response required before closure certification")
        if conclusion!="effective":raise ReviewConflictError("only effective independently retested remediation may close the regulatory finding")
        certs=self.repo.certifications(plan_id);seq=len(certs)+1;prev=certs[-1].certification_sha256 if certs else None
        source={"plan_sha256":p.plan_sha256,"tasks":[{"key":x.task_key,"status":x.status,"evidence":x.evidence_refs} for x in tasks],"checkpoints":[x.payload_sha256 for x in checkpoints],"retests":[x.payload_sha256 for x in retests],"followup":followups[-1].response_sha256}
        watermark=_sha(source);payload={"plan":plan_id,"sequence":seq,"conclusion":conclusion,"rationale":closure_rationale,"certifier":user_id,"watermark":watermark,"previous":prev}
        cert=self.repo.add(RegulatoryRemediationClosureCertificationModel(certification_id=f"rrz_{uuid4().hex}",tenant_id=self.tenant_id,plan_id=plan_id,certification_sequence=seq,conclusion=conclusion,closure_rationale=closure_rationale,certified_by_user_id=user_id,source_watermark_sha256=watermark,previous_certification_sha256=prev,certification_sha256=_sha(payload),certified_at=_now()))
        p.status="closed";p.updated_at=_now();finding=self._finding(p.examination_case_id,p.finding_code);finding.status="resolved";finding.resolved_by_user_id=user_id;finding.resolved_at=_now();case=self.exam.case(p.examination_case_id);case.status="remediation_certified";case.case_version+=1;case.updated_at=_now();self.session.flush();self._audit(p,"closure.certified","independent_human_closure_certifier",user_id,{"certification_id":cert.certification_id,"conclusion":conclusion,"source_watermark_sha256":watermark});self._emit("regulatory_remediation.closure.certified",p.plan_id,{"finding_code":p.finding_code,"certified_by":user_id});return cert
    def refresh_operations(self,actor_id="regulatory-remediation-worker",actor_type="monitoring_worker"):
        now=_now();updated=0
        for p in self.repo.plans():
            overdue=p.status!="closed" and _utc(p.due_at)<now
            task_overdue=any(t.status!="completed" and _utc(t.due_at)<now for t in self.repo.tasks(p.plan_id))
            if overdue or task_overdue:
                updated+=1;self._audit(p,"remediation.overdue","monitoring_worker",actor_id,{"plan_overdue":overdue,"task_overdue":task_overdue});self._emit("regulatory_remediation.overdue",p.plan_id,{"plan_overdue":overdue,"task_overdue":task_overdue})
        record_regulatory_remediation(metric="overdue_remediation_plans",value=updated,attributes={"tenant_id":self.tenant_id});return updated
    def dashboard(self,user_id):
        self._reader(user_id);now=_now();plans=self.repo.plans();return {"authority":REGULATORY_REMEDIATION_AUTHORITY,"kpis":{"plans":len(plans),"open":sum(x.status!="closed" for x in plans),"critical_high":sum(x.risk_level in {"critical","high"} for x in plans),"overdue":sum(x.status!="closed" and _utc(x.due_at)<now for x in plans),"closed":sum(x.status=="closed" for x in plans)},"plans":[self._plan_view(x) for x in plans]}
    def traceability(self,plan_id,user_id):
        self._reader(user_id);p=self._plan(plan_id);finding=self._finding(p.examination_case_id,p.finding_code)
        return {"plan":self._plan_view(p),"finding":{"finding_id":finding.finding_id,"finding_code":finding.finding_code,"severity":finding.severity,"material":finding.material,"status":finding.status,"source_refs":finding.source_refs},"tasks":[{"task_key":x.task_key,"task_type":x.task_type,"status":x.status,"dependencies":x.dependency_keys,"evidence_refs":x.evidence_refs} for x in self.repo.tasks(plan_id)],"checkpoints":[{"checkpoint_key":x.checkpoint_key,"type":x.checkpoint_type,"payload_sha256":x.payload_sha256,"evidence_refs":x.evidence_refs} for x in self.repo.checkpoints(plan_id)],"retests":[{"control_key":x.control_key,"sequence":x.retest_sequence,"outcome":x.outcome,"payload_sha256":x.payload_sha256,"evidence_refs":x.evidence_refs} for x in self.repo.retests(plan_id)],"waivers":[{"waiver_key":x.waiver_key,"status":x.status,"expires_at":x.expires_at} for x in self.repo.waivers(plan_id)],"followups":[{"followup_id":x.followup_id,"version":x.response_version,"status":x.status,"response_sha256":x.response_sha256,"previous_response_sha256":x.previous_response_sha256} for x in self.repo.followups(plan_id)],"certifications":[{"certification_id":x.certification_id,"sequence":x.certification_sequence,"conclusion":x.conclusion,"certified_by":x.certified_by_user_id,"certification_sha256":x.certification_sha256,"previous_certification_sha256":x.previous_certification_sha256} for x in self.repo.certifications(plan_id)],"audit_chain":[{"sequence":x.sequence,"event_type":x.event_type,"event_sha256":x.event_sha256,"previous_event_sha256":x.previous_event_sha256} for x in self.repo.audit(plan_id)],"provenance":"Release 52 regulator finding -> Release 53 versioned CAPA plan -> tasks/dependencies -> immutable implementation evidence -> independent control retest -> human follow-up response -> independent closure certification -> Release 52 examination closure","authority":REGULATORY_REMEDIATION_AUTHORITY}
    def audit_export(self,plan_id,user_id):
        trace=self.traceability(plan_id,user_id);manifest={"export_type":"regulatory_corrective_action_closure_assurance","plan_id":plan_id,"generated_at":_now().isoformat(),"traceability":trace};return {"manifest":manifest,"manifest_sha256":_sha(manifest),"immutable_source":True,"financial_accounting_mutation_authority":False,"human_remediation_approval_required":True}
    def _plan_view(self,p):return {"plan_id":p.plan_id,"examination_case_id":p.examination_case_id,"finding_code":p.finding_code,"plan_version":p.plan_version,"status":p.status,"risk_score":p.risk_score,"risk_level":p.risk_level,"owner_user_id":p.owner_user_id,"prepared_by_user_id":p.prepared_by_user_id,"approved_by_user_id":p.approved_by_user_id,"due_at":p.due_at,"ai_assisted":p.ai_assisted,"ai_authority":p.ai_authority,"plan_sha256":p.plan_sha256,"previous_plan_sha256":p.previous_plan_sha256}
    def _audit(self,p,event_type,actor_type,actor_id,details):
        chain=self.repo.audit(p.plan_id);seq=len(chain)+1;prev=chain[-1].event_sha256 if chain else None;payload={"plan_id":p.plan_id,"sequence":seq,"event_type":event_type,"actor_type":actor_type,"actor_id":actor_id,"details":details,"previous":prev};self.repo.add(RegulatoryRemediationAuditEventModel(audit_event_id=f"rrau_{uuid4().hex}",tenant_id=self.tenant_id,plan_id=p.plan_id,sequence=seq,event_type=event_type,actor_type=actor_type,actor_id=actor_id,details=details,previous_event_sha256=prev,event_sha256=_sha(payload),occurred_at=_now()))
    def _emit(self,event_type,aggregate_id,payload):enqueue_realtime_event(self.session,envelope=EventEnvelope(event_id=f"rt_{uuid4().hex}",event_type=event_type,tenant_id=self.tenant_id,claim_id=None,aggregate_type="regulatory_remediation",aggregate_id=str(aggregate_id),occurred_at=_now(),producer="medclaimiq-regulatory-remediation",payload=payload,metadata={"ai_authority":"recommendation_only","human_approval_required":True,"financial_accounting_mutation_authority":False,"fund_movement":False}),topic=EventTopic.CLAIMS.value)
