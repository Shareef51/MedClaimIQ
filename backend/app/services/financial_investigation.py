from __future__ import annotations
import hashlib,json,secrets
from datetime import UTC,datetime,timedelta
from decimal import Decimal
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.domain.financial_investigation import ROOT_CAUSE_CODES,REMEDIATION_TYPES
from app.domain.realtime import EventEnvelope,EventTopic
from app.models.claims import ClaimModel
from app.models.financial_intelligence import FinancialAnomalyInvestigationModel
from app.models.financial_investigation import *
from app.models.financial_handoff import PaymentIntentModel
from app.repositories.financial_investigation import FinancialInvestigationRepository
from app.repositories.tenancy import MembershipRepository
from app.realtime.events import enqueue_realtime_event
from app.services.financial_intelligence import FinancialIntelligenceService
from app.services.financial_handoff import FinancialHandoffService
from app.services.accounting_ledger import AccountingLedgerService
from app.services.review_workbench import ReviewConflictError,ReviewLockError

def _now():return datetime.now(UTC)
def _canon(v):return json.dumps(v,sort_keys=True,separators=(",",":"),default=str)
def _sha(v):return hashlib.sha256((v if isinstance(v,str) else _canon(v)).encode()).hexdigest()

def _recommended_root(anomaly_code:str)->str:
    a=anomaly_code.lower()
    if "duplicate" in a:return "duplicate_payment"
    if "overpay" in a:return "overpayment"
    if "return" in a:return "returned_payment"
    if "reserve" in a:return "reserve_inadequacy"
    if "provider" in a:return "provider_billing_pattern"
    if "account" in a or "close" in a:return "accounting_control_gap"
    return "reconciliation_mismatch"

def _case_type(anomaly_code:str)->str:
    a=anomaly_code.lower()
    if "reserve" in a:return "reserve_review"
    if "duplicate" in a or "overpay" in a:return "duplicate_overpayment"
    if "provider" in a:return "provider_payment_integrity"
    if "account" in a or "close" in a:return "accounting_control"
    return "payment_integrity"

class FinancialInvestigationService:
    INVESTIGATOR_ROLES={"finance_operator","finance_analyst"}
    READ_ROLES=INVESTIGATOR_ROLES|{"finance_approver","accounting_controller","auditor","tenant_admin"}
    def __init__(self,session:Session,tenant_id:str,*,material_amount:Decimal=Decimal("100.00")):
        self.session=session;self.tenant_id=tenant_id;self.repo=FinancialInvestigationRepository(session,tenant_id);self.members=MembershipRepository(session,tenant_id);self.material_amount=Decimal(str(material_amount))
    def _membership(self,user_id):
        m=self.members.get_by_user(user_id)
        if m is None or m.status!="active":raise ReviewConflictError("active human tenant membership required")
        return m
    def _require_reader(self,user_id):
        m=self._membership(user_id)
        if m.role not in self.READ_ROLES:raise ReviewConflictError("finance investigation read membership required")
        return m
    def _require_investigator(self,user_id):
        m=self._membership(user_id)
        if m.role not in self.INVESTIGATOR_ROLES:raise ReviewConflictError("human finance operator/analyst investigator required")
        return m
    def _require_approver(self,user_id):
        m=self._membership(user_id)
        if m.role!="finance_approver":raise ReviewConflictError("independent human finance approver required")
        return m
    def _case(self,case_id,for_update=False):
        c=self.repo.case(case_id,for_update=for_update)
        if c is None:raise LookupError("financial investigation case not found")
        return c
    def _assert_version(self,c,expected):
        if c.case_version!=expected:raise ReviewConflictError("stale financial investigation case version")
    def _emit(self,c,event_type,payload):
        enqueue_realtime_event(self.session,envelope=EventEnvelope(event_id=f"fic_{uuid4().hex}",event_type=event_type,tenant_id=self.tenant_id,claim_id=c.claim_id,aggregate_type="financial_investigation_case",aggregate_id=c.case_id,occurred_at=_now(),producer="medclaimiq-financial-investigation",payload=payload,metadata={"status":c.status,"case_id":c.case_id}),topic=EventTopic.CLAIMS.value)
    def _audit(self,c,event_type,actor_type,actor_id,payload,idempotency_key):
        existing=self.session.scalar(select(FinancialInvestigationAuditEventModel).where(FinancialInvestigationAuditEventModel.tenant_id==self.tenant_id,FinancialInvestigationAuditEventModel.idempotency_key==idempotency_key))
        if existing:return existing
        prior=self.repo.audit(c.case_id);seq=self.repo.next_audit_sequence(c.case_id);prev=prior[-1].event_sha256 if prior else None;now=_now();safe_payload=json.loads(_canon(payload));digest=_sha({"case_id":c.case_id,"sequence":seq,"event_type":event_type,"actor_type":actor_type,"actor_id":actor_id,"payload":safe_payload,"previous":prev,"occurred_at":now})
        return self.repo.add(FinancialInvestigationAuditEventModel(audit_event_id=f"ficaud_{uuid4().hex}",tenant_id=self.tenant_id,case_id=c.case_id,sequence=seq,event_type=event_type,actor_type=actor_type,actor_id=actor_id,payload=safe_payload,previous_event_sha256=prev,event_sha256=digest,idempotency_key=idempotency_key,occurred_at=now))
    def _task(self,c,task_type,key,due_hours,priority):
        existing=self.session.scalar(select(FinancialInvestigationTaskModel).where(FinancialInvestigationTaskModel.tenant_id==self.tenant_id,FinancialInvestigationTaskModel.idempotency_key==key))
        if existing:return existing
        return self.repo.add(FinancialInvestigationTaskModel(task_id=f"fictask_{uuid4().hex}",tenant_id=self.tenant_id,case_id=c.case_id,task_type=task_type,status="open",priority=priority,due_at=_now()+timedelta(hours=due_hours),assigned_user_id=c.assigned_investigator_user_id,idempotency_key=key,created_at=_now(),completed_at=None))
    def _complete_tasks(self,c,task_type):
        for t in self.repo.tasks(c.case_id):
            if t.task_type==task_type and t.status=="open":t.status="completed";t.completed_at=_now()
    def _build_pack(self,c,inv):
        analytics=FinancialIntelligenceService(self.session,self.tenant_id).claim_analytics(c.claim_id,persist=False)
        related=[x.case_id for x in self.repo.cluster_cases(c.cluster_key) if x.case_id!=c.case_id]
        items=[{"type":"release42_anomaly_investigation","id":inv.investigation_id,"sha256":inv.payload_sha256,"anomaly_code":inv.anomaly_code,"score":inv.anomaly_score},{"type":"claim_financial_analytics","id":c.claim_id,"sha256":analytics["source_watermark_sha256"],"metrics":analytics["metrics"]}]
        for cit in analytics.get("citations",[]):items.append({"type":cit.get("type","financial_source"),"id":cit.get("citation_id"),"sha256":cit.get("sha256")})
        payload={"case_id":c.case_id,"source_watermark_sha256":analytics["source_watermark_sha256"],"evidence_items":items,"citations":analytics.get("citations",[]),"related_case_ids":related}
        return self.repo.add(FinancialInvestigationEvidencePackModel(evidence_pack_id=f"fiev_{uuid4().hex}",tenant_id=self.tenant_id,case_id=c.case_id,pack_version=1,source_watermark_sha256=analytics["source_watermark_sha256"],evidence_items=items,citations=analytics.get("citations",[]),related_case_ids=related,payload_sha256=_sha(payload),created_at=_now()))
    def create_from_anomaly(self,investigation_id,actor_user_id=None,*,actor_type="human",idempotency_key):
        if actor_type=="human":self._require_investigator(actor_user_id)
        inv=self.session.scalar(select(FinancialAnomalyInvestigationModel).where(FinancialAnomalyInvestigationModel.tenant_id==self.tenant_id,FinancialAnomalyInvestigationModel.investigation_id==investigation_id))
        if inv is None or not inv.claim_id:raise LookupError("Release 42 anomaly investigation not found")
        existing=self.repo.source_case(investigation_id)
        if existing:return existing
        claim=self.session.scalar(select(ClaimModel).where(ClaimModel.tenant_id==self.tenant_id,ClaimModel.claim_id==inv.claim_id));
        if claim is None:raise LookupError("claim not found")
        case_type=_case_type(inv.anomaly_code);cluster_key=f"{case_type}:{claim.provider_organization_id}:{inv.anomaly_code}";now=_now();recommended=_recommended_root(inv.anomaly_code)
        c=self.repo.add(FinancialInvestigationCaseModel(case_id=f"ficase_{uuid4().hex}",tenant_id=self.tenant_id,claim_id=inv.claim_id,source_investigation_id=inv.investigation_id,anomaly_code=inv.anomaly_code,anomaly_score=inv.anomaly_score,severity=inv.severity,case_type=case_type,cluster_key=cluster_key,provider_organization_id=claim.provider_organization_id,status="open",priority=min(100,max(20,inv.anomaly_score)),assigned_investigator_user_id=None,root_cause_code=None,root_cause_rationale=None,ai_recommendation={"recommended_root_cause":recommended,"recommendations":inv.recommendations,"authority":"none"},ai_disagreement_rationale=None,case_version=1,created_by_actor_type=actor_type,created_by_actor_id=actor_user_id,created_at=now,updated_at=now,closed_at=None,closure_reason_code=None,closure_rationale=None))
        pack=self._build_pack(c,inv);self._task(c,"investigation_triage",f"triage:{c.case_id}",4,c.priority);self._audit(c,"financial_investigation.case.created",actor_type,actor_user_id,{"source_investigation_id":inv.investigation_id,"evidence_pack_sha256":pack.payload_sha256},f"audit:create:{idempotency_key}");self._emit(c,"financial_investigation.case.created",{"case_id":c.case_id,"status":c.status,"severity":c.severity});return c
    def acquire_lease(self,case_id,user_id,*,expected_case_version,lease_minutes=30):
        self._require_investigator(user_id);c=self._case(case_id,for_update=True);self._assert_version(c,expected_case_version);now=_now();existing=self.repo.lease(case_id,for_update=True)
        if existing:
            cmp_now=now if existing.expires_at.tzinfo is not None else now.replace(tzinfo=None)
            if existing.expires_at>cmp_now and existing.investigator_user_id!=user_id:raise ReviewLockError("financial investigation is leased by another human investigator")
        raw=secrets.token_urlsafe(32);digest=_sha(raw)
        if existing:
            existing.investigator_user_id=user_id;existing.lease_token_sha256=digest;existing.lease_version+=1;existing.acquired_at=now;existing.expires_at=now+timedelta(minutes=lease_minutes)
        else:existing=self.repo.add(FinancialInvestigationLeaseModel(case_id=case_id,tenant_id=self.tenant_id,investigator_user_id=user_id,lease_token_sha256=digest,lease_version=1,acquired_at=now,expires_at=now+timedelta(minutes=lease_minutes)))
        c.assigned_investigator_user_id=user_id;c.status="investigating";c.case_version+=1;c.updated_at=now;self._complete_tasks(c,"investigation_triage");self._task(c,"investigation_review",f"review:{c.case_id}",24,c.priority);self._audit(c,"financial_investigation.lease.acquired","human",user_id,{"lease_version":existing.lease_version,"expires_at":existing.expires_at},f"audit:lease:{case_id}:{existing.lease_version}");self._emit(c,"financial_investigation.lease.acquired",{"case_id":c.case_id,"status":c.status,"lease_version":existing.lease_version});return {"case":c,"lease_token":raw,"lease_version":existing.lease_version,"expires_at":existing.expires_at}
    def _assert_lease(self,c,user_id,token):
        l=self.repo.lease(c.case_id)
        now=_now()
        expired=True if l is None else l.expires_at <= (now if l.expires_at.tzinfo is not None else now.replace(tzinfo=None))
        if l is None or l.investigator_user_id!=user_id or expired or not secrets.compare_digest(l.lease_token_sha256,_sha(token)):raise ReviewLockError("valid exclusive human investigator lease required")
        return l
    def annotate(self,case_id,user_id,*,target_type,target_id,body,tags,idempotency_key):
        self._require_investigator(user_id);c=self._case(case_id);existing=self.session.scalar(select(FinancialInvestigationAnnotationModel).where(FinancialInvestigationAnnotationModel.tenant_id==self.tenant_id,FinancialInvestigationAnnotationModel.idempotency_key==idempotency_key))
        if existing:return existing
        row=self.repo.add(FinancialInvestigationAnnotationModel(annotation_id=f"fiann_{uuid4().hex}",tenant_id=self.tenant_id,case_id=case_id,reviewer_user_id=user_id,target_type=target_type,target_id=target_id,body=body,tags=tags,body_sha256=_sha({"body":body,"tags":tags,"target":target_id}),idempotency_key=idempotency_key,created_at=_now()));self._audit(c,"financial_investigation.annotation.added","human",user_id,{"annotation_id":row.annotation_id,"target_id":target_id},f"audit:{idempotency_key}");self._emit(c,"financial_investigation.annotation.added",{"case_id":c.case_id,"annotation_id":row.annotation_id});return row
    def classify_root_cause(self,case_id,user_id,*,root_cause_code,rationale,ai_disagreement_rationale,expected_case_version,lease_token):
        self._require_investigator(user_id);c=self._case(case_id,for_update=True);self._assert_version(c,expected_case_version);self._assert_lease(c,user_id,lease_token)
        if root_cause_code not in ROOT_CAUSE_CODES:raise ReviewConflictError("unsupported root-cause code")
        recommended=(c.ai_recommendation or {}).get("recommended_root_cause")
        if recommended and recommended!=root_cause_code and not (ai_disagreement_rationale or "").strip():raise ReviewConflictError("AI-vs-human disagreement rationale is required")
        c.root_cause_code=root_cause_code;c.root_cause_rationale=rationale;c.ai_disagreement_rationale=ai_disagreement_rationale;c.status="root_cause_classified";c.case_version+=1;c.updated_at=_now();self._complete_tasks(c,"investigation_review");self._task(c,"remediation_review",f"remediation:{c.case_id}",12,c.priority);self._audit(c,"financial_investigation.root_cause.classified","human",user_id,{"root_cause_code":root_cause_code,"ai_recommendation":recommended,"disagreement":bool(ai_disagreement_rationale)},f"audit:root:{c.case_id}:{c.case_version}");self._emit(c,"financial_investigation.root_cause.classified",{"case_id":c.case_id,"root_cause_code":root_cause_code});return c
    def propose_remediation(self,case_id,user_id,*,remediation_type,amount,currency,reason_code,rationale,idempotency_key,lease_token):
        self._require_investigator(user_id);c=self._case(case_id);self._assert_lease(c,user_id,lease_token)
        if not c.root_cause_code:raise ReviewConflictError("human root-cause classification required before remediation")
        if remediation_type not in REMEDIATION_TYPES:raise ReviewConflictError("unsupported remediation type")
        existing=self.session.scalar(select(FinancialRemediationProposalModel).where(FinancialRemediationProposalModel.tenant_id==self.tenant_id,FinancialRemediationProposalModel.idempotency_key==idempotency_key));
        if existing:return existing
        pack=self.repo.latest_pack(case_id);value=Decimal(str(amount));material=remediation_type in {"payment_hold","void_reissue_referral","adjustment_referral","recoupment_referral"} and value>=self.material_amount
        status="pending_second_approval" if material else "approved";payload={"case_id":case_id,"type":remediation_type,"amount":str(value),"root_cause":c.root_cause_code,"evidence_pack_sha256":pack.payload_sha256,"material":material}
        p=self.repo.add(FinancialRemediationProposalModel(proposal_id=f"firem_{uuid4().hex}",tenant_id=self.tenant_id,case_id=case_id,claim_id=c.claim_id,remediation_type=remediation_type,amount=value,currency=currency,reason_code=reason_code,rationale=rationale,evidence_pack_sha256=pack.payload_sha256,root_cause_code=c.root_cause_code,material=material,status=status,proposed_by_user_id=user_id,approved_by_user_id=None,approval_rationale=None,referral_type=None,referral_id=None,payload_sha256=_sha(payload),idempotency_key=idempotency_key,created_at=_now(),approved_at=None,executed_at=None));self._audit(c,"financial_investigation.remediation.proposed","human",user_id,{"proposal_id":p.proposal_id,"type":remediation_type,"material":material},f"audit:{idempotency_key}");self._emit(c,"financial_investigation.remediation.proposed",{"case_id":case_id,"proposal_id":p.proposal_id,"status":p.status,"material":material});return p
    def approve_remediation(self,case_id,proposal_id,approver_user_id,*,rationale,idempotency_key):
        self._require_approver(approver_user_id);c=self._case(case_id);p=self.session.scalar(select(FinancialRemediationProposalModel).where(FinancialRemediationProposalModel.tenant_id==self.tenant_id,FinancialRemediationProposalModel.proposal_id==proposal_id,FinancialRemediationProposalModel.case_id==case_id).with_for_update())
        if p is None:raise LookupError("remediation proposal not found")
        if not p.material:return p
        if p.proposed_by_user_id==approver_user_id:raise ReviewConflictError("material remediation requires a different human finance approver")
        if p.status=="approved":return p
        if p.status!="pending_second_approval":raise ReviewConflictError("proposal is not awaiting second approval")
        p.status="approved";p.approved_by_user_id=approver_user_id;p.approval_rationale=rationale;p.approved_at=_now();self._audit(c,"financial_investigation.remediation.second_approved","human",approver_user_id,{"proposal_id":p.proposal_id},f"audit:{idempotency_key}");self._emit(c,"financial_investigation.remediation.second_approved",{"case_id":case_id,"proposal_id":p.proposal_id,"status":p.status});return p
    def execute_referral(self,case_id,proposal_id,user_id,*,lease_token,idempotency_key):
        self._require_investigator(user_id);c=self._case(case_id);self._assert_lease(c,user_id,lease_token);p=self.session.scalar(select(FinancialRemediationProposalModel).where(FinancialRemediationProposalModel.tenant_id==self.tenant_id,FinancialRemediationProposalModel.proposal_id==proposal_id,FinancialRemediationProposalModel.case_id==case_id).with_for_update())
        if p is None:raise LookupError("remediation proposal not found")
        if p.status=="executed":return p
        if p.status!="approved":raise ReviewConflictError("remediation must be human-approved before referral execution")
        ref_type=None;ref_id=None
        if p.remediation_type=="payment_hold":
            r=FinancialHandoffService(self.session,self.tenant_id).place_hold(c.claim_id,user_id,hold_type="payment_integrity_investigation",reason_code=p.reason_code,rationale=p.rationale,idempotency_key=f"release43:{p.proposal_id}");ref_type="payment_hold";ref_id=r.hold_id
        elif p.remediation_type=="void_reissue_referral":
            intent=self.session.scalar(select(PaymentIntentModel).where(PaymentIntentModel.tenant_id==self.tenant_id,PaymentIntentModel.claim_id==c.claim_id).order_by(PaymentIntentModel.created_at.desc()).limit(1))
            if intent is None:raise ReviewConflictError("payment intent required for void/reissue referral")
            r=FinancialHandoffService(self.session,self.tenant_id).request_void_reissue(c.claim_id,intent.payment_intent_id,user_id,action="void",reason=p.rationale,idempotency_key=f"release43:{p.proposal_id}");ref_type="void_reissue_request";ref_id=r.request_id
        elif p.remediation_type in {"adjustment_referral","recoupment_referral"}:
            intent=self.session.scalar(select(PaymentIntentModel).where(PaymentIntentModel.tenant_id==self.tenant_id,PaymentIntentModel.claim_id==c.claim_id).order_by(PaymentIntentModel.created_at.desc()).limit(1))
            if intent is None:raise ReviewConflictError("payment intent required for accounting referral")
            kind="recoupment" if p.remediation_type=="recoupment_referral" else "adjustment";r=AccountingLedgerService(self.session,self.tenant_id).request_adjustment(c.claim_id,intent.payment_intent_id,user_id,adjustment_type=kind,amount=p.amount,reason_code=p.reason_code,rationale=p.rationale,idempotency_key=f"release43:{p.proposal_id}");ref_type=f"accounting_{kind}_request";ref_id=r.adjustment_id
        elif p.remediation_type=="reserve_review_referral":ref_type="reserve_review_task";ref_id=self._task(c,"reserve_review",f"reserve:{p.proposal_id}",24,c.priority).task_id
        else:ref_type="no_financial_action";ref_id=p.proposal_id
        p.status="executed";p.referral_type=ref_type;p.referral_id=ref_id;p.executed_at=_now();self._audit(c,"financial_investigation.remediation.referred","human",user_id,{"proposal_id":p.proposal_id,"referral_type":ref_type,"referral_id":ref_id},f"audit:{idempotency_key}");self._emit(c,"financial_investigation.remediation.referred",{"case_id":case_id,"proposal_id":p.proposal_id,"referral_type":ref_type});return p
    def close_case(self,case_id,user_id,*,reason_code,rationale,expected_case_version,lease_token,idempotency_key):
        self._require_investigator(user_id);c=self._case(case_id,for_update=True);self._assert_version(c,expected_case_version);self._assert_lease(c,user_id,lease_token)
        if not c.root_cause_code:raise ReviewConflictError("human root-cause classification required before closure")
        pending=[p for p in self.repo.proposals(case_id) if p.status in {"proposed","pending_second_approval"}]
        if pending:raise ReviewConflictError("unresolved remediation proposal blocks investigation closure")
        c.status="closed";c.closure_reason_code=reason_code;c.closure_rationale=rationale;c.closed_at=_now();c.updated_at=c.closed_at;c.case_version+=1
        for t in self.repo.tasks(case_id):
            if t.status=="open":t.status="completed";t.completed_at=_now()
        self._audit(c,"financial_investigation.case.closed","human",user_id,{"reason_code":reason_code,"root_cause_code":c.root_cause_code},f"audit:{idempotency_key}");self._emit(c,"financial_investigation.case.closed",{"case_id":case_id,"status":"closed","reason_code":reason_code});return c
    def workbench(self,case_id,user_id):
        self._require_reader(user_id);c=self._case(case_id);pack=self.repo.latest_pack(case_id);lease=self.repo.lease(case_id);cluster=self.repo.cluster_cases(c.cluster_key)
        return {"case":self._case_view(c),"evidence_pack":None if pack is None else {"evidence_pack_id":pack.evidence_pack_id,"pack_version":pack.pack_version,"source_watermark_sha256":pack.source_watermark_sha256,"evidence_items":pack.evidence_items,"citations":pack.citations,"related_case_ids":pack.related_case_ids,"payload_sha256":pack.payload_sha256},"lease":None if lease is None else {"investigator_user_id":lease.investigator_user_id,"lease_version":lease.lease_version,"expires_at":lease.expires_at},"cluster":[self._case_view(x) for x in cluster],"annotations":[{"annotation_id":x.annotation_id,"reviewer_user_id":x.reviewer_user_id,"target_type":x.target_type,"target_id":x.target_id,"body":x.body,"tags":x.tags,"body_sha256":x.body_sha256,"created_at":x.created_at} for x in self.repo.annotations(case_id)],"remediation_proposals":[self._proposal_view(x) for x in self.repo.proposals(case_id)],"tasks":[{"task_id":x.task_id,"task_type":x.task_type,"status":x.status,"priority":x.priority,"due_at":x.due_at,"assigned_user_id":x.assigned_user_id} for x in self.repo.tasks(case_id)],"audit_chain":[{"sequence":x.sequence,"event_type":x.event_type,"actor_type":x.actor_type,"actor_id":x.actor_id,"previous_event_sha256":x.previous_event_sha256,"event_sha256":x.event_sha256,"occurred_at":x.occurred_at} for x in self.repo.audit(case_id)],"authority":{"ai":"recommendation_only","adjudication":"none","accounting":"none","payment_authorization":"none","fund_movement":"none","human_investigator_required":True}}
    def queue(self,user_id):
        self._require_reader(user_id);now=_now();return [{**self._case_view(c),"sla_breached":any(t.status=="open" and t.due_at<now for t in self.repo.tasks(c.case_id))} for c in self.repo.cases()]
    def traceability(self,case_id,user_id):
        w=self.workbench(case_id,user_id);c=w["case"];nodes=[{"id":c["source_investigation_id"],"type":"release42_anomaly"},{"id":case_id,"type":"financial_investigation_case"}];edges=[{"from":c["source_investigation_id"],"to":case_id,"relation":"created_case"}]
        if w["evidence_pack"]:nodes.append({"id":w["evidence_pack"]["evidence_pack_id"],"type":"immutable_evidence_pack","sha256":w["evidence_pack"]["payload_sha256"]});edges.append({"from":case_id,"to":w["evidence_pack"]["evidence_pack_id"],"relation":"bound_evidence"})
        for p in w["remediation_proposals"]:
            nodes.append({"id":p["proposal_id"],"type":"governed_remediation","status":p["status"],"referral_id":p["referral_id"]});edges.append({"from":case_id,"to":p["proposal_id"],"relation":"human_proposed_remediation"})
            if p["referral_id"]:
                nodes.append({"id":p["referral_id"],"type":p["referral_type"],"governed_downstream":True});edges.append({"from":p["proposal_id"],"to":p["referral_id"],"relation":"governed_referral"})
        financial_lineage=FinancialHandoffService(self.session,self.tenant_id).traceability(c["claim_id"])
        accounting_lineage=AccountingLedgerService(self.session,self.tenant_id).traceability(c["claim_id"])
        return {"case_id":case_id,"nodes":nodes,"edges":edges,"downstream_financial_reconciliation":financial_lineage,"downstream_accounting_reconciliation":accounting_lineage,"authority":{"automation_changes_governed_finance":False,"automation_moves_funds":False}}
    @staticmethod
    def _case_view(c):return {"case_id":c.case_id,"claim_id":c.claim_id,"source_investigation_id":c.source_investigation_id,"anomaly_code":c.anomaly_code,"anomaly_score":c.anomaly_score,"severity":c.severity,"case_type":c.case_type,"cluster_key":c.cluster_key,"provider_organization_id":c.provider_organization_id,"status":c.status,"priority":c.priority,"assigned_investigator_user_id":c.assigned_investigator_user_id,"root_cause_code":c.root_cause_code,"root_cause_rationale":c.root_cause_rationale,"ai_recommendation":c.ai_recommendation,"ai_disagreement_rationale":c.ai_disagreement_rationale,"case_version":c.case_version,"created_at":c.created_at,"updated_at":c.updated_at,"closed_at":c.closed_at,"closure_reason_code":c.closure_reason_code,"closure_rationale":c.closure_rationale}
    @staticmethod
    def _proposal_view(p):return {"proposal_id":p.proposal_id,"remediation_type":p.remediation_type,"amount":str(p.amount),"currency":p.currency,"reason_code":p.reason_code,"rationale":p.rationale,"evidence_pack_sha256":p.evidence_pack_sha256,"root_cause_code":p.root_cause_code,"material":p.material,"status":p.status,"proposed_by_user_id":p.proposed_by_user_id,"approved_by_user_id":p.approved_by_user_id,"approval_rationale":p.approval_rationale,"referral_type":p.referral_type,"referral_id":p.referral_id,"payload_sha256":p.payload_sha256}
