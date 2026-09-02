from __future__ import annotations
import hashlib,json
from datetime import UTC,datetime,timedelta
from decimal import Decimal
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.domain.recovery_settlement import EVIDENCE_TYPES
from app.domain.realtime import EventEnvelope,EventTopic
from app.models.accounting_ledger import AccountingPeriodModel,LedgerJournalModel
from app.models.provider_dispute_resolution import ProviderDisputeFinalResolutionModel,RecoveryPositionVersionModel
from app.models.recovery_operations import RecoveryCaseModel
from app.models.recovery_settlement import *
from app.repositories.recovery_settlement import RecoverySettlementRepository
from app.repositories.tenancy import MembershipRepository
from app.realtime.events import enqueue_realtime_event
from app.services.review_workbench import ReviewConflictError

def _now():return datetime.now(UTC)
def _canon(v):return json.dumps(v,sort_keys=True,separators=(",",":"),default=str)
def _sha(v):return hashlib.sha256((v if isinstance(v,str) else _canon(v)).encode()).hexdigest()

class RecoverySettlementService:
    VERIFY_ROLES={"finance_operator","finance_analyst"};READ_ROLES=VERIFY_ROLES|{"finance_approver","accounting_controller","auditor","tenant_admin"}
    def __init__(self,session:Session,tenant_id:str):self.session=session;self.tenant_id=tenant_id;self.repo=RecoverySettlementRepository(session,tenant_id);self.members=MembershipRepository(session,tenant_id)
    def _membership(self,user_id):
        m=self.members.get_by_user(user_id)
        if m is None or m.status!="active":raise ReviewConflictError("active human tenant membership required")
        return m
    def _reader(self,user_id):
        m=self._membership(user_id)
        if m.role not in self.READ_ROLES:raise ReviewConflictError("financial settlement read membership required")
        return m
    def _verifier(self,user_id):
        m=self._membership(user_id)
        if m.role not in self.VERIFY_ROLES:raise ReviewConflictError("human finance operator/analyst required")
        return m
    def _approver(self,user_id):
        m=self._membership(user_id)
        if m.role!="finance_approver":raise ReviewConflictError("independent human finance approver required")
        return m
    def _case(self,case_id,for_update=False):
        c=self.repo.case(case_id,for_update)
        if c is None:raise LookupError("recovery settlement case not found")
        return c
    def _assert_version(self,c,expected):
        if c.case_version!=expected:raise ReviewConflictError("stale recovery settlement case version")
    def _emit(self,c,event_type,payload,trace_id=None):
        enqueue_realtime_event(self.session,envelope=EventEnvelope(event_id=f"rs_{uuid4().hex}",event_type=event_type,tenant_id=self.tenant_id,claim_id=c.claim_id,aggregate_type="recovery_settlement",aggregate_id=c.settlement_case_id,occurred_at=_now(),trace_id=trace_id,producer="medclaimiq-recovery-settlement",payload=payload,metadata={"recovery_case_id":c.recovery_case_id,"settlement_case_id":c.settlement_case_id,"status":c.status}),topic=EventTopic.CLAIMS.value)
    def _audit(self,c,event_type,actor_type,actor_id,payload,key):
        existing=self.session.scalar(select(RecoverySettlementAuditEventModel).where(RecoverySettlementAuditEventModel.tenant_id==self.tenant_id,RecoverySettlementAuditEventModel.idempotency_key==key))
        if existing:return existing
        rows=self.repo.audit(c.settlement_case_id);seq=self.repo.next_audit_sequence(c.settlement_case_id);prev=rows[-1].event_sha256 if rows else None;now=_now();safe=json.loads(_canon(payload));digest=_sha({"case":c.settlement_case_id,"seq":seq,"event":event_type,"actor_type":actor_type,"actor_id":actor_id,"payload":safe,"previous":prev,"occurred_at":now})
        return self.repo.add(RecoverySettlementAuditEventModel(audit_event_id=f"rsaud_{uuid4().hex}",tenant_id=self.tenant_id,settlement_case_id=c.settlement_case_id,sequence=seq,event_type=event_type,actor_type=actor_type,actor_id=actor_id,payload=safe,previous_event_sha256=prev,event_sha256=digest,idempotency_key=key,occurred_at=now))
    def _task(self,c,task_type,key,hours,priority=70):
        existing=self.session.scalar(select(RecoverySettlementTaskModel).where(RecoverySettlementTaskModel.tenant_id==self.tenant_id,RecoverySettlementTaskModel.idempotency_key==key))
        if existing:return existing
        return self.repo.add(RecoverySettlementTaskModel(task_id=f"rstask_{uuid4().hex}",tenant_id=self.tenant_id,settlement_case_id=c.settlement_case_id,task_type=task_type,status="open",priority=priority,due_at=_now()+timedelta(hours=hours),idempotency_key=key,created_at=_now(),completed_at=None))
    def _complete_tasks(self,c,*types):
        for t in self.repo.tasks(c.settlement_case_id):
            if t.status=="open" and (not types or t.task_type in types):t.status="completed";t.completed_at=_now()
    def create_from_recovery(self,recovery_case_id,user_id,*,idempotency_key,trace_id=None):
        self._verifier(user_id);existing=self.repo.by_recovery(recovery_case_id)
        if existing:return existing
        recovery=self.session.scalar(select(RecoveryCaseModel).where(RecoveryCaseModel.tenant_id==self.tenant_id,RecoveryCaseModel.recovery_case_id==recovery_case_id))
        if recovery is None:raise LookupError("recovery case not found")
        final=self.session.scalar(select(ProviderDisputeFinalResolutionModel).where(ProviderDisputeFinalResolutionModel.tenant_id==self.tenant_id,ProviderDisputeFinalResolutionModel.recovery_case_id==recovery_case_id).order_by(ProviderDisputeFinalResolutionModel.resolved_at.desc()).limit(1))
        if final is None:raise ReviewConflictError("Release 46 final human provider-dispute resolution required before settlement closeout")
        position=self.session.get(RecoveryPositionVersionModel,final.position_version_id)
        if position is None or position.tenant_id!=self.tenant_id:raise ReviewConflictError("controlling recovery position unavailable")
        latest=self.session.scalar(select(RecoveryPositionVersionModel).where(RecoveryPositionVersionModel.tenant_id==self.tenant_id,RecoveryPositionVersionModel.recovery_case_id==recovery_case_id).order_by(RecoveryPositionVersionModel.sequence.desc()).limit(1))
        if latest is None or latest.position_version_id!=position.position_version_id:raise ReviewConflictError("Release 46 resolution is not the latest controlling recovery position")
        target=Decimal(position.target_recovery_amount);now=_now();status="ready_for_closeout" if target==0 else "awaiting_settlement_evidence"
        c=self.repo.add(RecoverySettlementCaseModel(settlement_case_id=f"rsc_{uuid4().hex}",tenant_id=self.tenant_id,recovery_case_id=recovery_case_id,claim_id=recovery.claim_id,provider_organization_id=recovery.provider_organization_id,final_resolution_id=final.resolution_id,position_version_id=position.position_version_id,position_payload_sha256=position.payload_sha256,target_amount=target,verified_amount=Decimal("0"),remaining_amount=target,currency=recovery.currency,status=status,case_version=1,created_at=now,updated_at=now,certified_at=None))
        if target>0:self._task(c,"settlement_evidence_due",f"settlement-evidence:{c.settlement_case_id}",72,80)
        self._task(c,"financial_closeout",f"financial-closeout:{c.settlement_case_id}",168,75);self._audit(c,"recovery_settlement.case.created","human_finance_operator",user_id,{"target_amount":str(target),"position_version_id":position.position_version_id,"position_payload_sha256":position.payload_sha256},f"audit:create:{idempotency_key}");self._emit(c,"recovery_settlement.case.created",{"status":c.status,"target_amount":str(target)},trace_id);return c
    def _provider_or_finance(self,c,user_id):
        m=self._membership(user_id)
        if m.role=="provider":
            if not c.provider_organization_id or m.provider_organization_id!=c.provider_organization_id:raise ReviewConflictError("provider is not related to this recovery settlement")
        elif m.role not in self.READ_ROLES:raise ReviewConflictError("provider or authorized finance user required")
        return m
    def submit_evidence(self,case_id,user_id,*,evidence_type,amount,currency,installment_sequence,external_reference,bank_reference,remittance_reference,provider_reference,evidence_refs,occurred_at,idempotency_key,trace_id=None):
        c=self._case(case_id,True);self._provider_or_finance(c,user_id)
        if c.status=="certified":raise ReviewConflictError("certified settlement is immutable")
        if evidence_type not in EVIDENCE_TYPES:raise ValueError("unsupported recovery settlement evidence type")
        amount=Decimal(str(amount));currency=currency.upper()
        if amount<=0:raise ValueError("settlement evidence amount must be positive")
        existing=self.session.scalar(select(RecoverySettlementEvidenceModel).where(RecoverySettlementEvidenceModel.tenant_id==self.tenant_id,RecoverySettlementEvidenceModel.idempotency_key==idempotency_key))
        if existing:return existing
        payload={"type":evidence_type,"amount":str(amount),"currency":currency,"installment":installment_sequence,"external_reference":external_reference,"bank_reference":bank_reference,"remittance_reference":remittance_reference,"provider_reference":provider_reference,"evidence_refs":evidence_refs}
        row=self.repo.add(RecoverySettlementEvidenceModel(settlement_evidence_id=f"rsev_{uuid4().hex}",tenant_id=self.tenant_id,settlement_case_id=case_id,recovery_case_id=c.recovery_case_id,evidence_type=evidence_type,amount=amount,currency=currency,installment_sequence=installment_sequence,external_reference=external_reference,bank_reference=bank_reference,remittance_reference=remittance_reference,provider_reference=provider_reference,evidence_refs=evidence_refs,evidence_payload_sha256=_sha(payload),status="pending_verification",reference_match=None,verification_rationale=None,submitted_by_user_id=user_id,verified_by_user_id=None,idempotency_key=idempotency_key,occurred_at=occurred_at or _now(),created_at=_now(),verified_at=None))
        c.status="evidence_pending_verification";c.case_version+=1;c.updated_at=_now();self._audit(c,"recovery_settlement.evidence.submitted","human_provider" if self._membership(user_id).role=="provider" else "human_finance",user_id,{"settlement_evidence_id":row.settlement_evidence_id,"evidence_type":evidence_type,"amount":str(amount)},f"audit:evidence:{idempotency_key}");self._emit(c,"recovery_settlement.evidence.submitted",{"settlement_evidence_id":row.settlement_evidence_id,"status":row.status},trace_id);return row
    def _reference_complete(self,row):
        return {"bank_repayment":bool(row.bank_reference),"provider_remittance":bool(row.remittance_reference),"recoupment_offset":bool(row.remittance_reference or row.external_reference),"refund_credit":bool(row.external_reference)}[row.evidence_type]
    def _open_exception(self,c,code,details,severity="high"):
        existing=self.session.scalar(select(RecoverySettlementExceptionModel).where(RecoverySettlementExceptionModel.tenant_id==self.tenant_id,RecoverySettlementExceptionModel.settlement_case_id==c.settlement_case_id,RecoverySettlementExceptionModel.exception_code==code,RecoverySettlementExceptionModel.status=="open"))
        if existing:return existing
        return self.repo.add(RecoverySettlementExceptionModel(exception_id=f"rsex_{uuid4().hex}",tenant_id=self.tenant_id,settlement_case_id=c.settlement_case_id,exception_code=code,severity=severity,details=details,status="open",created_at=_now(),resolved_by_user_id=None,resolved_at=None))
    def _recalculate(self,c):
        verified=sum((Decimal(x.amount) for x in self.repo.evidence(c.settlement_case_id) if x.status=="verified"),Decimal("0"));c.verified_amount=verified;c.remaining_amount=c.target_amount-verified
        if verified>c.target_amount:self._open_exception(c,"over_recovery",{"target":str(c.target_amount),"verified":str(verified)},"critical");c.status="exception"
        elif verified==c.target_amount:c.remaining_amount=Decimal("0");c.status="matched";self._complete_tasks(c,"settlement_evidence_due")
        elif verified>0:c.status="partial_settlement"
        else:c.status="awaiting_settlement_evidence"
        c.updated_at=_now()
    def verify_evidence(self,case_id,evidence_id,user_id,*,reference_match,verification_rationale,expected_case_version,idempotency_key,trace_id=None):
        self._verifier(user_id);c=self._case(case_id,True);self._assert_version(c,expected_case_version);row=self.session.get(RecoverySettlementEvidenceModel,evidence_id)
        if row is None or row.tenant_id!=self.tenant_id or row.settlement_case_id!=case_id:raise LookupError("settlement evidence not found")
        if row.status!="pending_verification":return row
        complete=self._reference_complete(row);currency_match=row.currency==c.currency;verified=bool(reference_match and complete and currency_match)
        row.reference_match=bool(reference_match and complete);row.verification_rationale=verification_rationale;row.verified_by_user_id=user_id;row.verified_at=_now();row.status="verified" if verified else "rejected"
        if not complete or not reference_match:self._open_exception(c,"reference_mismatch",{"settlement_evidence_id":evidence_id,"reference_complete":complete,"human_reference_match":reference_match})
        if not currency_match:self._open_exception(c,"currency_mismatch",{"settlement_evidence_id":evidence_id,"expected":c.currency,"actual":row.currency})
        self._recalculate(c);c.case_version+=1;self._audit(c,"recovery_settlement.evidence.verified","human_finance_verifier",user_id,{"settlement_evidence_id":evidence_id,"status":row.status,"reference_match":row.reference_match,"verified_amount":str(c.verified_amount)},f"audit:verify:{idempotency_key}");self._emit(c,"recovery_settlement.evidence.verified",{"settlement_evidence_id":evidence_id,"status":row.status,"remaining_amount":str(c.remaining_amount)},trace_id);return row
    def correlate_ledger(self,case_id,evidence_id,user_id,*,journal_id,amount,currency,idempotency_key,trace_id=None):
        self._verifier(user_id);c=self._case(case_id,True);row=self.session.get(RecoverySettlementEvidenceModel,evidence_id)
        if row is None or row.tenant_id!=self.tenant_id or row.settlement_case_id!=case_id:raise LookupError("settlement evidence not found")
        if row.status!="verified":raise ReviewConflictError("only verified settlement evidence can be correlated to the ledger")
        journal=self.session.get(LedgerJournalModel,journal_id)
        if journal is None or journal.tenant_id!=self.tenant_id or journal.claim_id!=c.claim_id:raise ReviewConflictError("ledger journal does not belong to this claim")
        amount=Decimal(str(amount));currency=currency.upper()
        if journal.status!="posted" or journal.currency!=currency or row.currency!=currency:raise ReviewConflictError("posted journal and settlement evidence currency must match")
        if amount<=0 or amount>row.amount:raise ValueError("correlation amount must be positive and not exceed evidence amount")
        existing=self.session.scalar(select(RecoveryLedgerCorrelationModel).where(RecoveryLedgerCorrelationModel.tenant_id==self.tenant_id,RecoveryLedgerCorrelationModel.settlement_evidence_id==evidence_id,RecoveryLedgerCorrelationModel.journal_id==journal_id))
        if existing:return existing
        payload={"settlement_evidence_id":evidence_id,"journal_id":journal_id,"period_id":journal.period_id,"amount":str(amount),"currency":currency,"journal_sha256":journal.journal_sha256}
        corr=self.repo.add(RecoveryLedgerCorrelationModel(correlation_id=f"rslc_{uuid4().hex}",tenant_id=self.tenant_id,settlement_case_id=case_id,settlement_evidence_id=evidence_id,journal_id=journal_id,period_id=journal.period_id,amount=amount,currency=currency,status="verified",correlation_payload_sha256=_sha(payload),verified_by_user_id=user_id,created_at=_now()));c.case_version+=1;c.updated_at=_now();self._audit(c,"recovery_settlement.ledger.correlated","human_finance_verifier",user_id,payload,f"audit:ledger:{idempotency_key}");self._emit(c,"recovery_settlement.ledger.correlated",{"correlation_id":corr.correlation_id,"journal_id":journal_id},trace_id);return corr
    def add_correspondence(self,case_id,user_id,*,direction,channel,subject,body,external_message_id,idempotency_key,trace_id=None):
        c=self._case(case_id);self._provider_or_finance(c,user_id);existing=self.session.scalar(select(RecoverySettlementCorrespondenceModel).where(RecoverySettlementCorrespondenceModel.tenant_id==self.tenant_id,RecoverySettlementCorrespondenceModel.idempotency_key==idempotency_key))
        if existing:return existing
        row=self.repo.add(RecoverySettlementCorrespondenceModel(correspondence_id=f"rscorr_{uuid4().hex}",tenant_id=self.tenant_id,settlement_case_id=case_id,direction=direction,channel=channel,subject=subject,body=body,external_message_id=external_message_id,body_sha256=_sha(body),actor_id=user_id,idempotency_key=idempotency_key,occurred_at=_now()));self._audit(c,"recovery_settlement.correspondence.recorded","human",user_id,{"correspondence_id":row.correspondence_id,"direction":direction,"channel":channel},f"audit:corr:{idempotency_key}");self._emit(c,"recovery_settlement.correspondence.recorded",{"correspondence_id":row.correspondence_id},trace_id);return row
    def resolve_exception(self,case_id,exception_id,user_id,*,rationale,expected_case_version,idempotency_key,trace_id=None):
        self._verifier(user_id);c=self._case(case_id,True);self._assert_version(c,expected_case_version);x=self.session.get(RecoverySettlementExceptionModel,exception_id)
        if x is None or x.tenant_id!=self.tenant_id or x.settlement_case_id!=case_id:raise LookupError("settlement exception not found")
        x.status="resolved";x.details={**x.details,"resolution_rationale":rationale};x.resolved_by_user_id=user_id;x.resolved_at=_now();c.case_version+=1;c.updated_at=_now();self._audit(c,"recovery_settlement.exception.resolved","human_finance_verifier",user_id,{"exception_id":exception_id,"exception_code":x.exception_code},f"audit:exception:{idempotency_key}");self._emit(c,"recovery_settlement.exception.resolved",{"exception_id":exception_id},trace_id);return x
    def prepare_certificate(self,case_id,user_id,*,accounting_period_id,reason_codes,rationale,expected_case_version,idempotency_key,trace_id=None):
        self._verifier(user_id);c=self._case(case_id,True);self._assert_version(c,expected_case_version);existing=self.repo.certificate(case_id)
        if existing:return existing
        if c.remaining_amount!=0 or c.verified_amount!=c.target_amount:
            raise ReviewConflictError("unresolved recovery balance blocks financial closeout")
        open_ex=[x for x in self.repo.exceptions(case_id) if x.status=="open"]
        if open_ex:raise ReviewConflictError("open settlement exceptions block financial closeout preparation")
        period=self.session.get(AccountingPeriodModel,accounting_period_id)
        if period is None or period.tenant_id!=self.tenant_id:raise ReviewConflictError("governed accounting period required")
        correlations=self.repo.correlations(case_id)
        if c.target_amount>0:
            correlated=sum((Decimal(x.amount) for x in correlations if x.status=="verified" and x.period_id==accounting_period_id),Decimal("0"))
            if correlated!=c.target_amount:
                raise ReviewConflictError("verified recovery must be fully correlated to governed ledger journals in the selected accounting period")
        now=_now();payload={"case":case_id,"position":c.position_payload_sha256,"target":str(c.target_amount),"verified":str(c.verified_amount),"remaining":str(c.remaining_amount),"period":accounting_period_id,"reason_codes":reason_codes,"rationale":rationale,"prepared_by":user_id,"evidence":[x.evidence_payload_sha256 for x in self.repo.evidence(case_id) if x.status=="verified"],"correlations":[x.correlation_payload_sha256 for x in correlations]}
        cert=self.repo.add(RecoveryCompletionCertificateModel(certificate_id=f"rscert_{uuid4().hex}",tenant_id=self.tenant_id,settlement_case_id=case_id,recovery_case_id=c.recovery_case_id,accounting_period_id=accounting_period_id,prepared_by_user_id=user_id,approved_by_user_id=None,target_amount=c.target_amount,verified_amount=c.verified_amount,remaining_amount=c.remaining_amount,currency=c.currency,reason_codes=reason_codes,rationale=rationale,status="prepared",payload_sha256=_sha(payload),idempotency_key=idempotency_key,prepared_at=now,certified_at=None));c.status="closeout_prepared";c.case_version+=1;c.updated_at=now;self._audit(c,"recovery_settlement.certificate.prepared","human_finance_verifier",user_id,{"certificate_id":cert.certificate_id,"payload_sha256":cert.payload_sha256,"accounting_period_id":accounting_period_id},f"audit:certificate:{idempotency_key}");self._emit(c,"recovery_settlement.certificate.prepared",{"certificate_id":cert.certificate_id,"status":cert.status},trace_id);return cert
    def decide_certificate(self,case_id,certificate_id,user_id,*,action,rationale,expected_case_version,idempotency_key,trace_id=None):
        self._membership(user_id);c=self._case(case_id,True);self._assert_version(c,expected_case_version);cert=self.session.get(RecoveryCompletionCertificateModel,certificate_id)
        if cert is None or cert.tenant_id!=self.tenant_id or cert.settlement_case_id!=case_id:raise LookupError("recovery completion certificate not found")
        if cert.prepared_by_user_id==user_id:raise ReviewConflictError("financial closeout approver must differ from certificate preparer")
        self._approver(user_id)
        if cert.status!="prepared":return cert
        if action not in {"approve","reject"}:raise ValueError("unsupported closeout decision")
        if action=="reject":cert.status="rejected";c.status="closeout_rejected"
        else:
            if c.remaining_amount!=0 or any(x.status=="open" for x in self.repo.exceptions(case_id)):raise ReviewConflictError("settlement state changed or unresolved exceptions remain")
            cert.status="certified";cert.approved_by_user_id=user_id;cert.certified_at=_now();c.status="certified";c.certified_at=cert.certified_at;self._complete_tasks(c)
            body=f"Recovery settlement closeout was certified by an independent human finance approver. Verified recovery: {c.verified_amount} {c.currency}; remaining balance: {c.remaining_amount}. This certificate verifies external evidence and accounting correlation and does not execute collection or payment."
            self.repo.add(RecoverySettlementCorrespondenceModel(correspondence_id=f"rscorr_{uuid4().hex}",tenant_id=self.tenant_id,settlement_case_id=case_id,direction="outbound",channel="portal",subject="Recovery settlement completion",body=body,external_message_id=None,body_sha256=_sha(body),actor_id=user_id,idempotency_key=f"certified:{cert.certificate_id}",occurred_at=_now()))
        c.case_version+=1;c.updated_at=_now();self._audit(c,"recovery_settlement.certificate.decided","human_finance_approver",user_id,{"certificate_id":certificate_id,"action":action,"status":cert.status,"rationale":rationale},f"audit:certificate-decision:{idempotency_key}");self._emit(c,"recovery_settlement.certificate.decided",{"certificate_id":certificate_id,"status":cert.status},trace_id);return cert
    def refresh_operational_exceptions(self):
        now=_now();created=0
        for c in self.repo.cases():
            if c.status=="certified":continue
            overdue=any(t.status=="open" and (t.due_at if t.due_at.tzinfo else t.due_at.replace(tzinfo=UTC))<now for t in self.repo.tasks(c.settlement_case_id))
            if overdue and c.remaining_amount>0:
                before=len(self.repo.exceptions(c.settlement_case_id));self._open_exception(c,"unresolved_balance",{"remaining":str(c.remaining_amount),"aging":"sla_breached"});created+=len(self.repo.exceptions(c.settlement_case_id))-before
        return created
    def workbench(self,case_id,user_id):
        self._reader(user_id);c=self._case(case_id);now=_now();age=max(0,(now-(c.created_at if c.created_at.tzinfo else c.created_at.replace(tzinfo=UTC))).days);bucket="0-2d" if age<=2 else "3-7d" if age<=7 else "8-30d" if age<=30 else "31+d";cert=self.repo.certificate(case_id)
        return {"case":self._view_case(c),"evidence":[self._view_evidence(x) for x in self.repo.evidence(case_id)],"ledger_correlations":[{"correlation_id":x.correlation_id,"settlement_evidence_id":x.settlement_evidence_id,"journal_id":x.journal_id,"period_id":x.period_id,"amount":str(x.amount),"currency":x.currency,"status":x.status,"correlation_payload_sha256":x.correlation_payload_sha256} for x in self.repo.correlations(case_id)],"exceptions":[{"exception_id":x.exception_id,"exception_code":x.exception_code,"severity":x.severity,"details":x.details,"status":x.status,"created_at":x.created_at} for x in self.repo.exceptions(case_id)],"certificate":None if cert is None else {"certificate_id":cert.certificate_id,"accounting_period_id":cert.accounting_period_id,"prepared_by_user_id":cert.prepared_by_user_id,"approved_by_user_id":cert.approved_by_user_id,"target_amount":str(cert.target_amount),"verified_amount":str(cert.verified_amount),"remaining_amount":str(cert.remaining_amount),"status":cert.status,"payload_sha256":cert.payload_sha256,"prepared_at":cert.prepared_at,"certified_at":cert.certified_at},"correspondence":[{"correspondence_id":x.correspondence_id,"direction":x.direction,"channel":x.channel,"subject":x.subject,"body_sha256":x.body_sha256,"external_message_id":x.external_message_id,"actor_id":x.actor_id,"occurred_at":x.occurred_at} for x in self.repo.correspondence(case_id)],"tasks":[{"task_id":x.task_id,"task_type":x.task_type,"status":x.status,"priority":x.priority,"due_at":x.due_at,"sla_breached":x.status=="open" and (x.due_at if x.due_at.tzinfo else x.due_at.replace(tzinfo=UTC))<now} for x in self.repo.tasks(case_id)],"aging":{"age_days":age,"bucket":bucket},"audit_chain":[{"sequence":x.sequence,"event_type":x.event_type,"actor_type":x.actor_type,"actor_id":x.actor_id,"previous_event_sha256":x.previous_event_sha256,"event_sha256":x.event_sha256,"occurred_at":x.occurred_at} for x in self.repo.audit(case_id)],"authority":{"ai":"matching_and_analysis_only","closeout":"independent_human_finance_approver_only","bank_transaction":"none","accounting_approval":"none","payment_authorization":"none","fund_movement":"none"}}
    def queue(self,user_id):self._reader(user_id);return [self._view_case(x) for x in self.repo.cases()]
    def portfolio(self,user_id):
        self._reader(user_id);rows=self.repo.cases();target=sum((x.target_amount for x in rows),Decimal("0"));verified=sum((x.verified_amount for x in rows),Decimal("0"));return {"cases":len(rows),"open_cases":sum(x.status!="certified" for x in rows),"target_recovery":str(target),"verified_recovery":str(verified),"remaining_balance":str(target-verified),"certified_cases":sum(x.status=="certified" for x in rows),"authority":"analytics_only"}
    def provider_cases(self,user_id):
        m=self._membership(user_id)
        if m.role!="provider" or not m.provider_organization_id:raise ReviewConflictError("provider membership required")
        return [self._view_case(x) for x in self.repo.cases() if x.provider_organization_id==m.provider_organization_id]
    def provider_workbench(self,case_id,user_id):
        c=self._case(case_id);self._provider_or_finance(c,user_id);return {"case":self._view_case(c),"evidence":[self._view_evidence(x) for x in self.repo.evidence(case_id)],"correspondence":[{"correspondence_id":x.correspondence_id,"direction":x.direction,"channel":x.channel,"subject":x.subject,"occurred_at":x.occurred_at} for x in self.repo.correspondence(case_id)],"notice":"Repayment/remittance evidence is verified by authorized human finance operations. The portal cannot initiate collection, bank transactions, accounting approval or fund movement."}
    def traceability(self,case_id,user_id):
        wb=self.workbench(case_id,user_id);c=wb["case"];return {"settlement_case_id":case_id,"recovery_case_id":c["recovery_case_id"],"final_resolution_id":c["final_resolution_id"],"controlling_position":{"position_version_id":c["position_version_id"],"position_payload_sha256":c["position_payload_sha256"],"target_amount":c["target_amount"]},"evidence":[{"settlement_evidence_id":x["settlement_evidence_id"],"status":x["status"],"payload_sha256":x["evidence_payload_sha256"]} for x in wb["evidence"]],"ledger_correlations":wb["ledger_correlations"],"certificate":wb["certificate"],"authority":{"automation_collects_funds":False,"automation_creates_bank_transaction":False,"automation_approves_accounting":False,"automation_authorizes_payment":False,"automation_closes_financial_recovery":False}}
    @staticmethod
    def _view_case(c):return {"settlement_case_id":c.settlement_case_id,"recovery_case_id":c.recovery_case_id,"claim_id":c.claim_id,"provider_organization_id":c.provider_organization_id,"final_resolution_id":c.final_resolution_id,"position_version_id":c.position_version_id,"position_payload_sha256":c.position_payload_sha256,"target_amount":str(c.target_amount),"verified_amount":str(c.verified_amount),"remaining_amount":str(c.remaining_amount),"currency":c.currency,"status":c.status,"case_version":c.case_version,"created_at":c.created_at,"updated_at":c.updated_at,"certified_at":c.certified_at}
    @staticmethod
    def _view_evidence(x):return {"settlement_evidence_id":x.settlement_evidence_id,"evidence_type":x.evidence_type,"amount":str(x.amount),"currency":x.currency,"installment_sequence":x.installment_sequence,"external_reference":x.external_reference,"bank_reference":x.bank_reference,"remittance_reference":x.remittance_reference,"provider_reference":x.provider_reference,"evidence_refs":x.evidence_refs,"evidence_payload_sha256":x.evidence_payload_sha256,"status":x.status,"reference_match":x.reference_match,"verification_rationale":x.verification_rationale,"submitted_by_user_id":x.submitted_by_user_id,"verified_by_user_id":x.verified_by_user_id,"occurred_at":x.occurred_at,"verified_at":x.verified_at}
