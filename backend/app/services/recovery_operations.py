from __future__ import annotations
import hashlib,json,secrets
from datetime import UTC,datetime,timedelta
from decimal import Decimal
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.domain.recovery_operations import CLOSURE_REASONS,DISPUTE_OUTCOMES,RECOVERY_TYPES
from app.domain.realtime import EventEnvelope,EventTopic
from app.models.financial_investigation import FinancialInvestigationCaseModel,FinancialRemediationProposalModel
from app.models.financial_handoff import PaymentHoldModel,PaymentVoidReissueModel
from app.models.accounting_ledger import AccountingAdjustmentModel,PaymentReconciliationModel,ProviderRemittanceStatusModel
from app.models.recovery_operations import *
from app.repositories.recovery_operations import RecoveryOperationsRepository
from app.repositories.tenancy import MembershipRepository
from app.realtime.events import enqueue_realtime_event
from app.services.financial_investigation import FinancialInvestigationService
from app.services.review_workbench import ReviewConflictError,ReviewLockError

def _now():return datetime.now(UTC)
def _canon(v):return json.dumps(v,sort_keys=True,separators=(",",":"),default=str)
def _sha(v):return hashlib.sha256((v if isinstance(v,str) else _canon(v)).encode()).hexdigest()

def _recovery_type(referral_type:str)->str:
    return {"accounting_recoupment_request":"recoupment_recovery","accounting_adjustment_request":"adjustment_recovery","payment_hold":"payment_hold_verification","void_reissue_request":"void_reissue_verification","reserve_review_task":"reserve_review_verification"}.get(referral_type,"adjustment_recovery")

class RecoveryOperationsService:
    INVESTIGATOR_ROLES={"finance_operator","finance_analyst"}
    READ_ROLES=INVESTIGATOR_ROLES|{"finance_approver","accounting_controller","auditor","tenant_admin"}
    def __init__(self,session:Session,tenant_id:str,*,material_dispute_amount:Decimal=Decimal("100.00")):
        self.session=session;self.tenant_id=tenant_id;self.repo=RecoveryOperationsRepository(session,tenant_id);self.members=MembershipRepository(session,tenant_id);self.material_dispute_amount=Decimal(str(material_dispute_amount))
    def _membership(self,user_id):
        m=self.members.get_by_user(user_id)
        if m is None or m.status!="active":raise ReviewConflictError("active human tenant membership required")
        return m
    def _require_reader(self,user_id):
        m=self._membership(user_id)
        if m.role not in self.READ_ROLES:raise ReviewConflictError("recovery operations read membership required")
        return m
    def _require_investigator(self,user_id):
        m=self._membership(user_id)
        if m.role not in self.INVESTIGATOR_ROLES:raise ReviewConflictError("human finance operator/analyst required")
        return m
    def _require_approver(self,user_id):
        m=self._membership(user_id)
        if m.role!="finance_approver":raise ReviewConflictError("independent human finance approver required")
        return m
    def _case(self,case_id,for_update=False):
        c=self.repo.case(case_id,for_update)
        if c is None:raise LookupError("recovery case not found")
        return c
    def _assert_version(self,c,expected):
        if c.case_version!=expected:raise ReviewConflictError("stale recovery case version")
    def _emit(self,c,event_type,payload):
        enqueue_realtime_event(self.session,envelope=EventEnvelope(event_id=f"rec_{uuid4().hex}",event_type=event_type,tenant_id=self.tenant_id,claim_id=c.claim_id,aggregate_type="recovery_case",aggregate_id=c.recovery_case_id,occurred_at=_now(),producer="medclaimiq-recovery-operations",payload=payload,metadata={"status":c.status,"recovery_case_id":c.recovery_case_id}),topic=EventTopic.CLAIMS.value)
    def _audit(self,c,event_type,actor_type,actor_id,payload,key):
        existing=self.session.scalar(select(RecoveryAuditEventModel).where(RecoveryAuditEventModel.tenant_id==self.tenant_id,RecoveryAuditEventModel.idempotency_key==key))
        if existing:return existing
        prior=self.repo.audit(c.recovery_case_id);seq=self.repo.next_audit_sequence(c.recovery_case_id);prev=prior[-1].event_sha256 if prior else None;now=_now();safe=json.loads(_canon(payload));digest=_sha({"case":c.recovery_case_id,"sequence":seq,"event":event_type,"actor_type":actor_type,"actor_id":actor_id,"payload":safe,"previous":prev,"occurred_at":now})
        return self.repo.add(RecoveryAuditEventModel(audit_event_id=f"recaud_{uuid4().hex}",tenant_id=self.tenant_id,recovery_case_id=c.recovery_case_id,sequence=seq,event_type=event_type,actor_type=actor_type,actor_id=actor_id,payload=safe,previous_event_sha256=prev,event_sha256=digest,idempotency_key=key,occurred_at=now))
    def _task(self,c,task_type,key,hours,priority=None):
        existing=self.session.scalar(select(RecoveryTaskModel).where(RecoveryTaskModel.tenant_id==self.tenant_id,RecoveryTaskModel.idempotency_key==key))
        if existing:return existing
        return self.repo.add(RecoveryTaskModel(task_id=f"rectask_{uuid4().hex}",tenant_id=self.tenant_id,recovery_case_id=c.recovery_case_id,task_type=task_type,status="open",priority=priority or c.priority,due_at=_now()+timedelta(hours=hours),assigned_user_id=c.assigned_investigator_user_id,idempotency_key=key,created_at=_now(),completed_at=None))
    def _complete(self,c,task_type):
        for t in self.repo.tasks(c.recovery_case_id):
            if t.task_type==task_type and t.status=="open":t.status="completed";t.completed_at=_now()
    def create_from_remediation(self,proposal_id,actor_user_id=None,*,actor_type="human",idempotency_key):
        if actor_type=="human":self._require_investigator(actor_user_id)
        p=self.session.scalar(select(FinancialRemediationProposalModel).where(FinancialRemediationProposalModel.tenant_id==self.tenant_id,FinancialRemediationProposalModel.proposal_id==proposal_id))
        if p is None:raise LookupError("Release 43 remediation proposal not found")
        if p.status!="executed" or not p.referral_id:raise ReviewConflictError("only executed governed remediation referrals can enter recovery operations")
        if p.remediation_type=="no_financial_action":raise ReviewConflictError("no-financial-action remediation does not create a recovery case")
        existing=self.repo.source_case(proposal_id)
        if existing:return existing
        fic=self.session.scalar(select(FinancialInvestigationCaseModel).where(FinancialInvestigationCaseModel.tenant_id==self.tenant_id,FinancialInvestigationCaseModel.case_id==p.case_id))
        if fic is None:raise LookupError("financial investigation case not found")
        now=_now();amount=Decimal(str(p.amount));c=self.repo.add(RecoveryCaseModel(recovery_case_id=f"recovery_{uuid4().hex}",tenant_id=self.tenant_id,claim_id=p.claim_id,financial_investigation_case_id=p.case_id,source_proposal_id=p.proposal_id,referral_type=p.referral_type or "unknown",referral_id=p.referral_id,recovery_type=_recovery_type(p.referral_type or ""),provider_organization_id=fic.provider_organization_id,currency=p.currency,identified_amount=amount,target_recovery_amount=amount,recovered_amount=Decimal("0"),status="open",priority=fic.priority,assigned_investigator_user_id=None,case_version=1,effectiveness_score=0,last_verified_at=None,created_at=now,updated_at=now,closed_at=None,closure_reason_code=None,closure_rationale=None))
        fin_trace=FinancialInvestigationService(self.session,self.tenant_id).traceability(p.case_id,actor_user_id) if actor_type=="human" else {"case_id":p.case_id,"authority":{"automation_moves_funds":False}}
        items=[{"type":"financial_investigation_case","id":p.case_id},{"type":"remediation_proposal","id":p.proposal_id,"sha256":p.payload_sha256},{"type":p.referral_type,"id":p.referral_id}]
        payload={"recovery_case_id":c.recovery_case_id,"source_proposal_id":p.proposal_id,"referral_id":p.referral_id,"items":items,"identified_amount":str(amount),"currency":p.currency,"upstream_authority":fin_trace.get("authority",{})};pack=self.repo.add(RecoveryEvidencePackModel(evidence_pack_id=f"recev_{uuid4().hex}",tenant_id=self.tenant_id,recovery_case_id=c.recovery_case_id,pack_version=1,evidence_items=items,citations=[{"type":"release43_remediation","id":p.proposal_id,"sha256":p.payload_sha256}],source_sha256=p.payload_sha256,payload_sha256=_sha(payload),created_at=now))
        self._task(c,"recovery_verification",f"recovery:verify:{c.recovery_case_id}",24);self._audit(c,"recovery.case.created",actor_type,actor_user_id,{"proposal_id":p.proposal_id,"evidence_pack_sha256":pack.payload_sha256},f"audit:create:{idempotency_key}");self._emit(c,"recovery.case.created",{"recovery_case_id":c.recovery_case_id,"recovery_type":c.recovery_type});return c
    def acquire_lease(self,case_id,user_id,*,expected_case_version,lease_minutes=30):
        self._require_investigator(user_id);c=self._case(case_id,True);self._assert_version(c,expected_case_version);now=_now();lease=self.repo.lease(case_id,True)
        if lease:
            cmp=now if lease.expires_at.tzinfo else now.replace(tzinfo=None)
            if lease.expires_at>cmp and lease.investigator_user_id!=user_id:raise ReviewLockError("recovery case already leased by another investigator")
            lease.lease_version+=1
        else:
            lease=self.repo.add(RecoveryLeaseModel(recovery_case_id=case_id,tenant_id=self.tenant_id,investigator_user_id=user_id,lease_token_sha256="",lease_version=1,acquired_at=now,expires_at=now))
        raw=secrets.token_urlsafe(32);lease.investigator_user_id=user_id;lease.lease_token_sha256=_sha(raw);lease.acquired_at=now;lease.expires_at=now+timedelta(minutes=lease_minutes);c.assigned_investigator_user_id=user_id;c.status="verifying";c.case_version+=1;c.updated_at=now;self._audit(c,"recovery.lease.acquired","human",user_id,{"lease_version":lease.lease_version},f"audit:lease:{case_id}:{lease.lease_version}");self._emit(c,"recovery.lease.acquired",{"lease_version":lease.lease_version});return {"case":c,"lease_token":raw,"lease_version":lease.lease_version,"expires_at":lease.expires_at}
    def _assert_lease(self,c,user_id,token):
        lease=self.repo.lease(c.recovery_case_id)
        if lease is None or lease.investigator_user_id!=user_id or lease.lease_token_sha256!=_sha(token):raise ReviewLockError("valid investigator lease required")
        now=_now();cmp=now if lease.expires_at.tzinfo else now.replace(tzinfo=None)
        if lease.expires_at<=cmp:raise ReviewLockError("investigator lease expired")
    def _downstream_state(self,c):
        if c.referral_type=="payment_hold":
            row=self.session.scalar(select(PaymentHoldModel).where(PaymentHoldModel.tenant_id==self.tenant_id,PaymentHoldModel.hold_id==c.referral_id));return {"source_type":"payment_hold","source_id":c.referral_id,"status":"active" if row and row.active else "released","verified":row is not None}
        if c.referral_type=="void_reissue_request":
            row=self.session.scalar(select(PaymentVoidReissueModel).where(PaymentVoidReissueModel.tenant_id==self.tenant_id,PaymentVoidReissueModel.request_id==c.referral_id));return {"source_type":"void_reissue_request","source_id":c.referral_id,"status":row.status if row else "missing","replacement_payment_intent_id":row.replacement_payment_intent_id if row else None,"verified":row is not None}
        if c.referral_type in {"accounting_adjustment_request","accounting_recoupment_request"}:
            row=self.session.scalar(select(AccountingAdjustmentModel).where(AccountingAdjustmentModel.tenant_id==self.tenant_id,AccountingAdjustmentModel.adjustment_id==c.referral_id));return {"source_type":c.referral_type,"source_id":c.referral_id,"status":row.status if row else "missing","journal_id":row.journal_id if row else None,"verified":row is not None}
        return {"source_type":c.referral_type,"source_id":c.referral_id,"status":"manual_verification_required","verified":False}
    def verify_remediation_outcome(self,case_id,user_id,*,lease_token,idempotency_key):
        self._require_investigator(user_id);c=self._case(case_id,True);self._assert_lease(c,user_id,lease_token);existing=self.session.scalar(select(RecoveryOutcomeModel).where(RecoveryOutcomeModel.tenant_id==self.tenant_id,RecoveryOutcomeModel.idempotency_key==idempotency_key))
        if existing:return existing
        state=self._downstream_state(c);now=_now();row=self.repo.add(RecoveryOutcomeModel(outcome_id=f"recout_{uuid4().hex}",tenant_id=self.tenant_id,recovery_case_id=case_id,outcome_type="remediation_verification",source_type=state["source_type"],source_id=state["source_id"],amount=Decimal("0"),currency=c.currency,status=state["status"],external_reference=None,details=state,payload_sha256=_sha(state),idempotency_key=idempotency_key,recorded_by_actor_type="human",recorded_by_actor_id=user_id,occurred_at=now));c.last_verified_at=now;c.updated_at=now;c.effectiveness_score=100 if state.get("verified") and state["status"] not in {"missing","pending","requested"} else 50 if state.get("verified") else 0;self._audit(c,"recovery.remediation.verified","human",user_id,{"outcome_id":row.outcome_id,"downstream":state},f"audit:{idempotency_key}");self._emit(c,"recovery.remediation.verified",{"outcome_id":row.outcome_id,"status":row.status});return row
    def record_recovery(self,case_id,user_id,*,amount,currency,external_reference,evidence_details,lease_token,idempotency_key):
        self._require_investigator(user_id);c=self._case(case_id,True);self._assert_lease(c,user_id,lease_token);value=Decimal(str(amount))
        if value<=0:raise ValueError("recovery amount must be positive")
        if currency!=c.currency:raise ReviewConflictError("recovery currency must match governed remediation currency")
        existing=self.session.scalar(select(RecoveryOutcomeModel).where(RecoveryOutcomeModel.tenant_id==self.tenant_id,RecoveryOutcomeModel.idempotency_key==idempotency_key))
        if existing:return existing
        cumulative=c.recovered_amount+value;c.recovered_amount=cumulative;c.status="recovered" if c.target_recovery_amount>0 and cumulative>=c.target_recovery_amount else "partial_recovery";c.effectiveness_score=100 if c.target_recovery_amount<=0 else min(100,int((cumulative/c.target_recovery_amount)*100));c.last_verified_at=_now();c.updated_at=c.last_verified_at;c.case_version+=1;details={"evidence":evidence_details,"cumulative_recovered":str(cumulative),"target":str(c.target_recovery_amount)}
        row=self.repo.add(RecoveryOutcomeModel(outcome_id=f"recout_{uuid4().hex}",tenant_id=self.tenant_id,recovery_case_id=case_id,outcome_type="external_recovery_evidence",source_type="external_recovery_evidence",source_id=external_reference,amount=value,currency=currency,status=c.status,external_reference=external_reference,details=details,payload_sha256=_sha(details),idempotency_key=idempotency_key,recorded_by_actor_type="human",recorded_by_actor_id=user_id,occurred_at=_now()));self._audit(c,"recovery.amount.recorded","human",user_id,{"amount":str(value),"cumulative":str(cumulative),"external_reference":external_reference},f"audit:{idempotency_key}");self._emit(c,"recovery.amount.recorded",{"amount":str(value),"recovered_amount":str(cumulative),"effectiveness_score":c.effectiveness_score});return row
    def submit_dispute(self,case_id,user_id,*,external_reference,disputed_amount,currency,reason_code,statement,evidence_refs,idempotency_key):
        c=self._case(case_id,True);m=self._membership(user_id)
        if m.role=="provider":
            if not c.provider_organization_id or m.provider_organization_id!=c.provider_organization_id:raise ReviewConflictError("provider membership is not related to this recovery case")
        elif m.role not in self.INVESTIGATOR_ROLES:raise ReviewConflictError("provider or human finance investigator required for dispute intake")
        existing=self.session.scalar(select(ProviderDisputeModel).where(ProviderDisputeModel.tenant_id==self.tenant_id,ProviderDisputeModel.external_reference==external_reference))
        if existing:return existing
        pack=self.repo.pack(case_id)
        if pack is None:raise ReviewConflictError("immutable recovery evidence pack required")
        value=Decimal(str(disputed_amount));material=value>=self.material_dispute_amount;payload={"case_id":case_id,"external_reference":external_reference,"amount":str(value),"currency":currency,"reason_code":reason_code,"statement":statement,"evidence_refs":evidence_refs,"evidence_pack_sha256":pack.payload_sha256};row=self.repo.add(ProviderDisputeModel(dispute_id=f"dispute_{uuid4().hex}",tenant_id=self.tenant_id,recovery_case_id=case_id,claim_id=c.claim_id,provider_organization_id=c.provider_organization_id or m.provider_organization_id or "unknown",external_reference=external_reference,disputed_amount=value,currency=currency,reason_code=reason_code,statement=statement,evidence_refs=evidence_refs,evidence_pack_sha256=pack.payload_sha256,material=material,status="escalated" if material else "open",submitted_by_user_id=user_id,assigned_resolver_user_id=None,resolution_outcome=None,resolution_rationale=None,resolution_amount=None,payload_sha256=_sha(payload),submitted_at=_now(),resolved_at=None));c.status="provider_dispute";c.case_version+=1;c.updated_at=_now();self._task(c,"material_dispute_resolution" if material else "provider_dispute_review",f"dispute:{row.dispute_id}",12 if material else 24,max(c.priority,85 if material else c.priority));self._audit(c,"recovery.dispute.submitted","human_provider" if m.role=="provider" else "human_finance",user_id,{"dispute_id":row.dispute_id,"material":material,"disputed_amount":str(value)},f"audit:dispute:{idempotency_key}");self._emit(c,"recovery.dispute.submitted",{"dispute_id":row.dispute_id,"material":material,"status":row.status});return row
    def resolve_dispute(self,case_id,dispute_id,approver_user_id,*,outcome,rationale,resolution_amount,idempotency_key):
        """Retired: final provider dispute adjudication must use the evidence-bound provider_dispute_resolution workflow."""
        raise ReviewConflictError("direct provider dispute resolution is retired; use the evidence-bound provider dispute resolution packet workflow")
    def add_correspondence(self,case_id,user_id,*,dispute_id,direction,channel,subject,body,external_message_id,idempotency_key):
        c=self._case(case_id);m=self._membership(user_id)
        if m.role not in self.READ_ROLES|{"provider"}:raise ReviewConflictError("provider or authorized finance user required")
        existing=self.session.scalar(select(RecoveryCorrespondenceModel).where(RecoveryCorrespondenceModel.tenant_id==self.tenant_id,RecoveryCorrespondenceModel.idempotency_key==idempotency_key))
        if existing:return existing
        row=self.repo.add(RecoveryCorrespondenceModel(correspondence_id=f"reccorr_{uuid4().hex}",tenant_id=self.tenant_id,recovery_case_id=case_id,dispute_id=dispute_id,direction=direction,channel=channel,subject=subject,body=body,external_message_id=external_message_id,body_sha256=_sha(body),actor_type="human",actor_id=user_id,idempotency_key=idempotency_key,occurred_at=_now()));self._audit(c,"recovery.correspondence.recorded","human",user_id,{"correspondence_id":row.correspondence_id,"direction":direction,"channel":channel},f"audit:corr:{idempotency_key}");self._emit(c,"recovery.correspondence.recorded",{"correspondence_id":row.correspondence_id});return row
    def close_case(self,case_id,user_id,*,reason_code,rationale,expected_case_version,lease_token,idempotency_key):
        self._require_investigator(user_id);c=self._case(case_id,True);self._assert_version(c,expected_case_version);self._assert_lease(c,user_id,lease_token)
        if reason_code not in CLOSURE_REASONS:raise ValueError("unsupported recovery closure reason")
        if any(d.status!="resolved" for d in self.repo.disputes(case_id)):raise ReviewConflictError("open provider dispute blocks recovery closure")
        if c.last_verified_at is None:raise ReviewConflictError("remediation outcome verification required before closure")
        c.status="closed";c.closure_reason_code=reason_code;c.closure_rationale=rationale;c.closed_at=_now();c.updated_at=c.closed_at;c.case_version+=1
        for t in self.repo.tasks(case_id):
            if t.status=="open":t.status="completed";t.completed_at=_now()
        self._audit(c,"recovery.case.closed","human_finance_investigator",user_id,{"reason_code":reason_code,"recovered_amount":str(c.recovered_amount),"identified_amount":str(c.identified_amount),"effectiveness_score":c.effectiveness_score},f"audit:close:{idempotency_key}");self._emit(c,"recovery.case.closed",{"reason_code":reason_code,"effectiveness_score":c.effectiveness_score});return c
    def workbench(self,case_id,user_id):
        self._require_reader(user_id);c=self._case(case_id);pack=self.repo.pack(case_id);lease=self.repo.lease(case_id);now=_now();outcomes=self.repo.outcomes(case_id);disputes=self.repo.disputes(case_id);tasks=self.repo.tasks(case_id)
        age_days=max(0,(now-c.created_at.replace(tzinfo=UTC) if c.created_at.tzinfo is None else now-c.created_at).days);aging_bucket="0-2d" if age_days<=2 else "3-7d" if age_days<=7 else "8-30d" if age_days<=30 else "31+d"
        return {"case":self._view_case(c),"evidence_pack":None if pack is None else {"evidence_pack_id":pack.evidence_pack_id,"pack_version":pack.pack_version,"evidence_items":pack.evidence_items,"citations":pack.citations,"source_sha256":pack.source_sha256,"payload_sha256":pack.payload_sha256},"lease":None if lease is None else {"investigator_user_id":lease.investigator_user_id,"lease_version":lease.lease_version,"expires_at":lease.expires_at},"downstream_state":self._downstream_state(c),"outcomes":[self._view_outcome(x) for x in outcomes],"disputes":[self._view_dispute(x) for x in disputes],"correspondence":[{"correspondence_id":x.correspondence_id,"dispute_id":x.dispute_id,"direction":x.direction,"channel":x.channel,"subject":x.subject,"body_sha256":x.body_sha256,"external_message_id":x.external_message_id,"actor_id":x.actor_id,"occurred_at":x.occurred_at} for x in self.repo.correspondence(case_id)],"tasks":[{"task_id":x.task_id,"task_type":x.task_type,"status":x.status,"priority":x.priority,"due_at":x.due_at,"sla_breached":x.status=="open" and (x.due_at if x.due_at.tzinfo is not None else x.due_at.replace(tzinfo=UTC))<now} for x in tasks],"aging":{"age_days":age_days,"bucket":aging_bucket},"effectiveness":{"identified_amount":str(c.identified_amount),"recovered_amount":str(c.recovered_amount),"recovered_vs_identified_percent":0 if c.identified_amount<=0 else round(float(c.recovered_amount/c.identified_amount*100),2),"score":c.effectiveness_score},"audit_chain":[{"sequence":x.sequence,"event_type":x.event_type,"actor_type":x.actor_type,"actor_id":x.actor_id,"previous_event_sha256":x.previous_event_sha256,"event_sha256":x.event_sha256,"occurred_at":x.occurred_at} for x in self.repo.audit(case_id)],"authority":{"ai":"analysis_and_recommendation_only","provider_dispute_resolution":"independent_human_only","accounting_change":"none","payment_authorization":"none","collection":"none","fund_movement":"none"}}
    def queue(self,user_id):
        self._require_reader(user_id);now=_now();return [{**self._view_case(c),"sla_breached":any(t.status=="open" and (t.due_at if t.due_at.tzinfo is not None else t.due_at.replace(tzinfo=UTC))<now for t in self.repo.tasks(c.recovery_case_id)),"open_disputes":sum(1 for d in self.repo.disputes(c.recovery_case_id) if d.status!="resolved")} for c in self.repo.cases()]
    def portfolio(self,user_id):
        self._require_reader(user_id);cases=self.repo.cases();identified=sum((c.identified_amount for c in cases),Decimal("0"));recovered=sum((c.recovered_amount for c in cases),Decimal("0"));open_disputes=sum(sum(1 for d in self.repo.disputes(c.recovery_case_id) if d.status!="resolved") for c in cases);return {"cases":len(cases),"open_cases":sum(c.status!="closed" for c in cases),"identified_leakage":str(identified),"verified_recovered":str(recovered),"recovery_rate_percent":0 if identified<=0 else round(float(recovered/identified*100),2),"open_provider_disputes":open_disputes,"authority":"analytics_only"}
    def traceability(self,case_id,user_id):
        w=self.workbench(case_id,user_id);c=w["case"];up=FinancialInvestigationService(self.session,self.tenant_id).traceability(c["financial_investigation_case_id"],user_id);nodes=[{"id":case_id,"type":"recovery_case"}];edges=[]
        for o in w["outcomes"]:nodes.append({"id":o["outcome_id"],"type":"recovery_outcome","status":o["status"]});edges.append({"from":case_id,"to":o["outcome_id"],"relation":"verified_outcome"})
        for d in w["disputes"]:nodes.append({"id":d["dispute_id"],"type":"provider_dispute","status":d["status"]});edges.append({"from":case_id,"to":d["dispute_id"],"relation":"provider_dispute"})
        return {"recovery_case_id":case_id,"upstream_anomaly_investigation_remediation":up,"nodes":nodes,"edges":edges,"downstream_state":w["downstream_state"],"effectiveness":w["effectiveness"],"authority":{"automation_adjudicates_dispute":False,"automation_changes_accounting":False,"automation_authorizes_payment":False,"automation_collects_or_moves_funds":False}}
    @staticmethod
    def _view_case(c):return {"recovery_case_id":c.recovery_case_id,"claim_id":c.claim_id,"financial_investigation_case_id":c.financial_investigation_case_id,"source_proposal_id":c.source_proposal_id,"referral_type":c.referral_type,"referral_id":c.referral_id,"recovery_type":c.recovery_type,"provider_organization_id":c.provider_organization_id,"currency":c.currency,"identified_amount":str(c.identified_amount),"target_recovery_amount":str(c.target_recovery_amount),"recovered_amount":str(c.recovered_amount),"status":c.status,"priority":c.priority,"assigned_investigator_user_id":c.assigned_investigator_user_id,"case_version":c.case_version,"effectiveness_score":c.effectiveness_score,"last_verified_at":c.last_verified_at,"created_at":c.created_at,"updated_at":c.updated_at,"closed_at":c.closed_at,"closure_reason_code":c.closure_reason_code,"closure_rationale":c.closure_rationale}
    @staticmethod
    def _view_outcome(x):return {"outcome_id":x.outcome_id,"outcome_type":x.outcome_type,"source_type":x.source_type,"source_id":x.source_id,"amount":str(x.amount),"currency":x.currency,"status":x.status,"external_reference":x.external_reference,"details":x.details,"payload_sha256":x.payload_sha256,"occurred_at":x.occurred_at}
    @staticmethod
    def _view_dispute(x):return {"dispute_id":x.dispute_id,"external_reference":x.external_reference,"disputed_amount":str(x.disputed_amount),"currency":x.currency,"reason_code":x.reason_code,"evidence_refs":x.evidence_refs,"evidence_pack_sha256":x.evidence_pack_sha256,"material":x.material,"status":x.status,"submitted_by_user_id":x.submitted_by_user_id,"assigned_resolver_user_id":x.assigned_resolver_user_id,"resolution_outcome":x.resolution_outcome,"resolution_rationale":x.resolution_rationale,"resolution_amount":None if x.resolution_amount is None else str(x.resolution_amount),"payload_sha256":x.payload_sha256,"submitted_at":x.submitted_at,"resolved_at":x.resolved_at}
