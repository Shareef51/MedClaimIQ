from __future__ import annotations
import hashlib,json
from calendar import monthrange
from datetime import UTC,date,datetime
from decimal import Decimal,ROUND_HALF_UP
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.domain.accounting_ledger import ACCOUNTING_AUTHORITY,AccountingPeriodStatus,ReconciliationStatus,AdjustmentStatus,AdjustmentType
from app.models.accounting_ledger import *
from app.models.financial_handoff import PaymentIntentModel,SettlementEventModel,FinancialAuthorizationPacketModel,FinancialReconciliationExceptionModel
from app.models.post_decision import DecisionHistoryVersionModel
from app.repositories.accounting_ledger import AccountingLedgerRepository
from app.repositories.financial_handoff import FinancialHandoffRepository
from app.repositories.tenancy import MembershipRepository
from app.domain.realtime import EventEnvelope,EventTopic
from app.realtime.events import enqueue_realtime_event
from app.services.review_workbench import ReviewConflictError

def _now():return datetime.now(UTC)
def _money(v):return Decimal(str(v)).quantize(Decimal("0.01"),rounding=ROUND_HALF_UP)
def _canonical(v):return json.dumps(v,sort_keys=True,separators=(",",":"),default=str)
def _sha(v):return hashlib.sha256((v if isinstance(v,str) else _canonical(v)).encode()).hexdigest()
def _utc(v):
    if v is None:return _now()
    return v.replace(tzinfo=UTC) if v.tzinfo is None else v.astimezone(UTC)

def _bucket(days:int)->str:
    if days<=2:return "0-2d"
    if days<=7:return "3-7d"
    if days<=30:return "8-30d"
    return "31+d"

class AccountingLedgerService:
    """Governed payer accounting ledger built on already human-authorized Release 40 instructions.

    It creates accounting evidence and balanced journal entries; it cannot authorize or execute fund movement.
    ERA/EFT records are treated as external reconciliation evidence, never adjudication or payment authority.
    """
    def __init__(self,session:Session,tenant_id:str):
        self.session=session;self.tenant_id=tenant_id;self.repo=AccountingLedgerRepository(session,tenant_id);self.fin=FinancialHandoffRepository(session,tenant_id)
    def _membership(self,user_id):
        m=MembershipRepository(self.session,self.tenant_id).get_by_user(user_id)
        if m is None or m.status!="active":raise ReviewConflictError("active tenant membership required")
        return m
    def _require_accounting_operator(self,user_id):
        m=self._membership(user_id)
        if m.role not in {"finance_operator","finance_analyst","accounting_controller"}:raise ReviewConflictError("human finance/accounting operator membership required")
        return m
    def _require_finance_approver(self,user_id):
        m=self._membership(user_id)
        if m.role!="finance_approver":raise ReviewConflictError("independent human finance approver membership required")
        return m
    def _require_controller(self,user_id):
        m=self._membership(user_id)
        if m.role!="accounting_controller":raise ReviewConflictError("human accounting controller membership required")
        return m
    def _intent(self,intent_id):
        row=self.fin.intent(intent_id)
        if row is None:raise LookupError("payment intent not found")
        return row
    def _authorized_packet(self,intent:PaymentIntentModel):
        p=self.fin.packet(intent.packet_id)
        if p is None or p.status!="authorized" or not p.authorized_by_user_id or not p.authorized_payload_sha256:raise ReviewConflictError("human-authorized immutable financial packet required")
        return p
    def _emit(self,claim_id,event_type,aggregate_type,aggregate_id,payload,trace_id=None):
        return enqueue_realtime_event(self.session,envelope=EventEnvelope(event_id=f"acct_{uuid4().hex}",event_type=event_type,tenant_id=self.tenant_id,claim_id=claim_id,aggregate_type=aggregate_type,aggregate_id=aggregate_id,occurred_at=_now(),trace_id=trace_id,producer="medclaimiq-accounting-ledger",payload=payload,metadata={k:v for k,v in payload.items() if k in {"status","payment_intent_id","reconciliation_id","period_id","journal_id"}}),topic=EventTopic.CLAIMS.value)
    def _period_for(self,ts:datetime|None=None):
        ts=_utc(ts);key=ts.strftime("%Y-%m");p=self.repo.period_by_key(key)
        if p:return p
        start=date(ts.year,ts.month,1);end=date(ts.year,ts.month,monthrange(ts.year,ts.month)[1])
        return self.repo.add(AccountingPeriodModel(period_id=f"period_{uuid4().hex}",tenant_id=self.tenant_id,period_key=key,start_date=start,end_date=end,status=AccountingPeriodStatus.OPEN.value,lock_version=1,close_summary={},close_sha256=None,closed_by_user_id=None,created_at=_now(),closed_at=None))
    def _assert_open_period(self,p):
        if p.status!=AccountingPeriodStatus.OPEN.value:raise ReviewConflictError("accounting period is closed; journal posting is prohibited")
    def _post_journal(self,*,claim_id,payment_intent_id,journal_type,source_type,source_id,currency,entries,actor_type,actor_id,idempotency_key,trace_id=None):
        existing=self.session.scalar(select(LedgerJournalModel).where(LedgerJournalModel.tenant_id==self.tenant_id,LedgerJournalModel.idempotency_key==idempotency_key))
        if existing:return existing
        debits=sum((_money(x[2]) for x in entries if x[0]=="debit"),Decimal("0.00"));credits=sum((_money(x[2]) for x in entries if x[0]=="credit"),Decimal("0.00"))
        if debits<=0 or debits!=credits:raise ReviewConflictError("double-entry journal must be non-zero and exactly balanced")
        period=self._period_for();self._assert_open_period(period);prior=self.repo.journals();prev=prior[-1].journal_sha256 if prior else None
        payload={"tenant_id":self.tenant_id,"claim_id":claim_id,"payment_intent_id":payment_intent_id,"period_id":period.period_id,"journal_type":journal_type,"source_type":source_type,"source_id":source_id,"currency":currency,"debits":str(debits),"credits":str(credits),"entries":[{"direction":d,"account_code":a,"amount":str(_money(v)),"memo":m} for d,a,v,m in entries],"previous":prev}
        row=self.repo.add(LedgerJournalModel(journal_id=f"journal_{uuid4().hex}",tenant_id=self.tenant_id,claim_id=claim_id,payment_intent_id=payment_intent_id,period_id=period.period_id,journal_type=journal_type,source_type=source_type,source_id=source_id,currency=currency,total_debits=debits,total_credits=credits,status="posted",previous_journal_sha256=prev,journal_sha256=_sha(payload),posted_by_actor_type=actor_type,posted_by_actor_id=actor_id,idempotency_key=idempotency_key,trace_id=trace_id,created_at=_now()))
        for seq,(direction,account,amount,memo) in enumerate(entries,1):
            self.repo.add(LedgerEntryModel(entry_id=f"entry_{uuid4().hex}",tenant_id=self.tenant_id,journal_id=row.journal_id,claim_id=claim_id,entry_sequence=seq,account_code=account,direction=direction,amount=_money(amount),currency=currency,memo=memo,created_at=_now()))
        self._emit(claim_id,"accounting.journal.posted","ledger_journal",row.journal_id,{"journal_id":row.journal_id,"payment_intent_id":payment_intent_id,"status":"posted"},trace_id);return row
    def record_era(self,claim_id,payment_intent_id,user_id,*,era_reference,payment_reference,provider_ref,paid_amount,currency="USD",remittance_payload=None,trace_id=None):
        self._require_accounting_operator(user_id);intent=self._intent(payment_intent_id);self._authorized_packet(intent)
        if intent.claim_id!=claim_id:raise ReviewConflictError("payment intent claim mismatch")
        existing=self.session.scalar(select(ERARecordModel).where(ERARecordModel.tenant_id==self.tenant_id,ERARecordModel.era_reference==era_reference))
        if existing:return existing
        amount=_money(paid_amount)
        if amount<=0:raise ReviewConflictError("ERA paid amount must be positive")
        payload=remittance_payload or {"era_reference":era_reference,"payment_reference":payment_reference,"provider_ref":provider_ref,"paid_amount":str(amount),"currency":currency}
        row=self.repo.add(ERARecordModel(era_id=f"era_{uuid4().hex}",tenant_id=self.tenant_id,claim_id=claim_id,payment_intent_id=payment_intent_id,era_reference=era_reference,payment_reference=payment_reference,provider_ref=provider_ref,paid_amount=amount,currency=currency,remittance_payload=payload,payload_sha256=_sha(payload),received_at=_now()))
        self._update_provider_status(intent,provider_ref);self._update_queue(intent);self._emit(claim_id,"accounting.era.received","era_record",row.era_id,{"payment_intent_id":payment_intent_id,"status":"received"},trace_id);return row
    def record_eft(self,claim_id,payment_intent_id,user_id,*,eft_reference,bank_reference,trace_number,amount,currency="USD",status="posted",trace_id=None):
        self._require_accounting_operator(user_id);intent=self._intent(payment_intent_id);self._authorized_packet(intent)
        if intent.claim_id!=claim_id:raise ReviewConflictError("payment intent claim mismatch")
        existing=self.session.scalar(select(EFTRecordModel).where(EFTRecordModel.tenant_id==self.tenant_id,EFTRecordModel.eft_reference==eft_reference))
        if existing:return existing
        value=_money(amount)
        if value<=0:raise ReviewConflictError("EFT amount must be positive")
        payload={"eft_reference":eft_reference,"bank_reference":bank_reference,"trace_number":trace_number,"amount":str(value),"currency":currency,"status":status}
        row=self.repo.add(EFTRecordModel(eft_id=f"eft_{uuid4().hex}",tenant_id=self.tenant_id,claim_id=claim_id,payment_intent_id=payment_intent_id,eft_reference=eft_reference,bank_reference=bank_reference,trace_number=trace_number,amount=value,currency=currency,status=status,payload_sha256=_sha(payload),received_at=_now()))
        self._update_queue(intent);self._emit(claim_id,"accounting.eft.received","eft_record",row.eft_id,{"payment_intent_id":payment_intent_id,"status":status},trace_id);return row
    def reconcile(self,claim_id,payment_intent_id,user_id,*,idempotency_key,trace_id=None):
        self._require_accounting_operator(user_id);intent=self._intent(payment_intent_id);packet=self._authorized_packet(intent)
        if intent.claim_id!=claim_id:raise ReviewConflictError("payment intent claim mismatch")
        eras=self.repo.eras(payment_intent_id);efts=self.repo.efts(payment_intent_id);expected=_money(intent.amount);era_total=sum((_money(x.paid_amount) for x in eras),Decimal("0.00"));eft_total=sum((_money(x.amount) for x in efts if x.status not in {"reversed","returned"}),Decimal("0.00"));matched=min(era_total,eft_total,expected);unmatched=max(Decimal("0.00"),expected-matched)
        era_refs={x.payment_reference for x in eras};eft_refs={x.bank_reference for x in efts}|{x.trace_number for x in efts};reference_match=bool(era_refs & eft_refs)
        currencies={x.currency for x in eras}|{x.currency for x in efts}|{intent.currency}
        if len(currencies)>1:status=ReconciliationStatus.EXCEPTION.value
        elif era_total==expected and eft_total==expected and reference_match:status=ReconciliationStatus.RECONCILED.value
        elif era_total>expected or eft_total>expected or (era_total and eft_total and not reference_match):status=ReconciliationStatus.EXCEPTION.value
        elif era_total or eft_total:status=ReconciliationStatus.PARTIAL.value
        else:status=ReconciliationStatus.OPEN.value
        now=_now();row=self.repo.reconciliation(payment_intent_id)
        digest=_sha({"intent":payment_intent_id,"expected":str(expected),"era_total":str(era_total),"eft_total":str(eft_total),"matched":str(matched),"reference_match":reference_match,"status":status,"era_refs":[x.era_reference for x in eras],"eft_refs":[x.eft_reference for x in efts],"decision_history_sha256":packet.decision_history_sha256})
        if row is None:
            row=self.repo.add(PaymentReconciliationModel(reconciliation_id=f"recon_{uuid4().hex}",tenant_id=self.tenant_id,claim_id=claim_id,payment_intent_id=payment_intent_id,expected_amount=expected,era_total=era_total,eft_total=eft_total,matched_amount=matched,unmatched_amount=unmatched,currency=intent.currency,reference_match=reference_match,status=status,era_refs=[x.era_reference for x in eras],eft_refs=[x.eft_reference for x in efts],journal_id=None,reconciliation_sha256=digest,created_at=now,updated_at=now,reconciled_at=now if status=="reconciled" else None))
        else:
            row.expected_amount=expected;row.era_total=era_total;row.eft_total=eft_total;row.matched_amount=matched;row.unmatched_amount=unmatched;row.reference_match=reference_match;row.status=status;row.era_refs=[x.era_reference for x in eras];row.eft_refs=[x.eft_reference for x in efts];row.reconciliation_sha256=digest;row.updated_at=now;row.reconciled_at=now if status=="reconciled" else None
        if status=="reconciled" and row.journal_id is None:
            journal=self._post_journal(claim_id=claim_id,payment_intent_id=payment_intent_id,journal_type="claim_payment_settlement",source_type="era_eft_reconciliation",source_id=row.reconciliation_id,currency=intent.currency,entries=[("debit","claims_payable",expected,"Clear human-authorized claim payable"),("credit","cash_clearing",expected,"Recognize externally settled EFT")],actor_type="human_finance_operator",actor_id=user_id,idempotency_key=f"settlement-journal:{payment_intent_id}:{row.reconciliation_sha256}",trace_id=trace_id);row.journal_id=journal.journal_id
        if status=="exception":self._ensure_exception_queue(intent,["era_eft_amount_or_reference_mismatch"])
        self._update_provider_status(intent,eras[-1].provider_ref if eras else intent.payee_ref);self._update_queue(intent,reconciliation=row)
        self._emit(claim_id,"accounting.reconciliation.updated","payment_reconciliation",row.reconciliation_id,{"reconciliation_id":row.reconciliation_id,"payment_intent_id":payment_intent_id,"status":status},trace_id);return row
    def record_return(self,claim_id,payment_intent_id,user_id,*,return_reference,return_code,amount,reason,currency="USD",trace_id=None):
        self._require_accounting_operator(user_id);intent=self._intent(payment_intent_id);self._authorized_packet(intent)
        existing=self.session.scalar(select(ReturnedPaymentModel).where(ReturnedPaymentModel.tenant_id==self.tenant_id,ReturnedPaymentModel.return_reference==return_reference))
        if existing:return existing
        value=_money(amount)
        if value<=0 or value>_money(intent.amount):raise ReviewConflictError("returned amount must be positive and not exceed authorized payment intent")
        row=self.repo.add(ReturnedPaymentModel(return_id=f"return_{uuid4().hex}",tenant_id=self.tenant_id,claim_id=claim_id,payment_intent_id=payment_intent_id,return_reference=return_reference,return_code=return_code,amount=value,currency=currency,reason=reason,status="recorded",journal_id=None,received_at=_now()))
        journal=self._post_journal(claim_id=claim_id,payment_intent_id=payment_intent_id,journal_type="returned_payment_reversal",source_type="returned_payment",source_id=row.return_id,currency=currency,entries=[("debit","cash_clearing",value,"Reverse cash for returned payment"),("credit","claims_payable",value,"Reinstate claim payable after return")],actor_type="human_finance_operator",actor_id=user_id,idempotency_key=f"return-journal:{return_reference}",trace_id=trace_id);row.journal_id=journal.journal_id;row.status="journaled"
        recon=self.repo.reconciliation(payment_intent_id)
        if recon:recon.status=ReconciliationStatus.RETURNED.value;recon.updated_at=_now()
        self._update_provider_status(intent,intent.payee_ref,status_override="returned");self._ensure_exception_queue(intent,["returned_payment"]);self._emit(claim_id,"accounting.payment.returned","returned_payment",row.return_id,{"payment_intent_id":payment_intent_id,"status":"returned"},trace_id);return row
    def request_adjustment(self,claim_id,payment_intent_id,user_id,*,adjustment_type,amount,reason_code,rationale,idempotency_key):
        self._require_accounting_operator(user_id);intent=self._intent(payment_intent_id);self._authorized_packet(intent)
        if adjustment_type not in {x.value for x in AdjustmentType}:raise ReviewConflictError("unsupported adjustment type")
        existing=self.session.scalar(select(AccountingAdjustmentModel).where(AccountingAdjustmentModel.tenant_id==self.tenant_id,AccountingAdjustmentModel.idempotency_key==idempotency_key))
        if existing:return existing
        value=_money(amount)
        if value<=0:raise ReviewConflictError("adjustment amount must be positive")
        return self.repo.add(AccountingAdjustmentModel(adjustment_id=f"adj_{uuid4().hex}",tenant_id=self.tenant_id,claim_id=claim_id,payment_intent_id=payment_intent_id,adjustment_type=adjustment_type,amount=value,currency=intent.currency,reason_code=reason_code,rationale=rationale,status=AdjustmentStatus.PENDING_APPROVAL.value,requested_by_user_id=user_id,approved_by_user_id=None,journal_id=None,idempotency_key=idempotency_key,created_at=_now(),approved_at=None))
    def approve_adjustment(self,claim_id,adjustment_id,approver_user_id,*,rationale,idempotency_key,trace_id=None):
        self._require_finance_approver(approver_user_id);row=self.session.scalar(select(AccountingAdjustmentModel).where(AccountingAdjustmentModel.tenant_id==self.tenant_id,AccountingAdjustmentModel.adjustment_id==adjustment_id))
        if row is None or row.claim_id!=claim_id:raise LookupError("accounting adjustment not found")
        if row.requested_by_user_id==approver_user_id:raise ReviewConflictError("segregation of duties requires a different human finance approver")
        if row.status==AdjustmentStatus.POSTED.value:return row
        if row.status!=AdjustmentStatus.PENDING_APPROVAL.value:raise ReviewConflictError("adjustment is not pending approval")
        row.approved_by_user_id=approver_user_id;row.approved_at=_now();row.status=AdjustmentStatus.APPROVED.value
        if row.adjustment_type==AdjustmentType.ADJUSTMENT.value:
            entries=[("debit","claims_adjustment_expense",row.amount,"Approved accounting adjustment expense"),("credit","claims_payable",row.amount,"Increase claim payable for approved adjustment")]
        else:
            entries=[("debit","provider_recoupment_receivable",row.amount,"Recognize approved provider recoupment receivable"),("credit","claims_adjustment_recovery",row.amount,"Recognize approved claim recoupment recovery")]
        j=self._post_journal(claim_id=claim_id,payment_intent_id=row.payment_intent_id,journal_type=row.adjustment_type,source_type="accounting_adjustment",source_id=row.adjustment_id,currency=row.currency,entries=entries,actor_type="human_finance_approver",actor_id=approver_user_id,idempotency_key=f"adjustment-journal:{row.adjustment_id}:{idempotency_key}",trace_id=trace_id);row.journal_id=j.journal_id;row.status=AdjustmentStatus.POSTED.value
        self._emit(claim_id,"accounting.adjustment.posted","accounting_adjustment",row.adjustment_id,{"payment_intent_id":row.payment_intent_id,"status":"posted"},trace_id);return row
    def _update_provider_status(self,intent,provider_ref,status_override=None):
        eras=self.repo.eras(intent.payment_intent_id);efts=self.repo.efts(intent.payment_intent_id);recon=self.repo.reconciliation(intent.payment_intent_id);row=self.repo.remittance_status(intent.payment_intent_id);amount=sum((_money(x.paid_amount) for x in eras),Decimal("0.00"));status=status_override or (recon.status if recon else ("remittance_received" if eras else "pending"));now=_now()
        if row is None:return self.repo.add(ProviderRemittanceStatusModel(status_id=f"providerremit_{uuid4().hex}",tenant_id=self.tenant_id,claim_id=intent.claim_id,payment_intent_id=intent.payment_intent_id,provider_ref=provider_ref,status=status,remitted_amount=amount,currency=intent.currency,latest_era_reference=eras[-1].era_reference if eras else None,latest_eft_reference=efts[-1].eft_reference if efts else None,updated_at=now))
        row.provider_ref=provider_ref;row.status=status;row.remitted_amount=amount;row.latest_era_reference=eras[-1].era_reference if eras else row.latest_era_reference;row.latest_eft_reference=efts[-1].eft_reference if efts else row.latest_eft_reference;row.updated_at=now;return row
    def _ensure_exception_queue(self,intent,codes):
        self._update_queue(intent,exception_codes=codes)
    def _update_queue(self,intent,reconciliation=None,exception_codes=None):
        row=self.session.scalar(select(AccountingReconciliationQueueModel).where(AccountingReconciliationQueueModel.tenant_id==self.tenant_id,AccountingReconciliationQueueModel.payment_intent_id==intent.payment_intent_id));age=max(0,(_now()-_utc(intent.created_at)).days);bucket=_bucket(age);status="closed" if reconciliation and reconciliation.status=="reconciled" else "open";codes=exception_codes or ([] if reconciliation is None or reconciliation.status!="exception" else ["era_eft_reconciliation_exception"]);priority=90 if codes else (80 if age>30 else 60 if age>7 else 40);now=_now()
        if row is None:return self.repo.add(AccountingReconciliationQueueModel(queue_id=f"acctq_{uuid4().hex}",tenant_id=self.tenant_id,claim_id=intent.claim_id,payment_intent_id=intent.payment_intent_id,status=status,age_days=age,aging_bucket=bucket,priority=priority,exception_codes=codes,assigned_user_id=None,created_at=now,updated_at=now,closed_at=now if status=="closed" else None))
        row.status=status;row.age_days=age;row.aging_bucket=bucket;row.priority=priority;row.exception_codes=codes;row.updated_at=now;row.closed_at=now if status=="closed" else None;return row
    def refresh_aging_queue(self,user_id):
        self._require_accounting_operator(user_id)
        intents=list(self.session.scalars(select(PaymentIntentModel).where(PaymentIntentModel.tenant_id==self.tenant_id)))
        for i in intents:self._update_queue(i,reconciliation=self.repo.reconciliation(i.payment_intent_id))
        return self.repo.queue()
    def refresh_aging_queue_system(self):
        """Background-safe calculation only: updates queue age/priority; never posts journals, approves adjustments, closes periods, or moves funds."""
        intents=list(self.session.scalars(select(PaymentIntentModel).where(PaymentIntentModel.tenant_id==self.tenant_id)))
        for i in intents:self._update_queue(i,reconciliation=self.repo.reconciliation(i.payment_intent_id))
        return self.repo.queue()
    def close_period(self,period_id,controller_user_id,*,expected_lock_version,rationale,idempotency_key,trace_id=None):
        self._require_controller(controller_user_id);p=self.repo.period(period_id)
        if p is None:raise LookupError("accounting period not found")
        if p.status==AccountingPeriodStatus.CLOSED.value:return p
        if p.lock_version!=expected_lock_version:raise ReviewConflictError("stale accounting period version")
        start_dt=datetime.combine(p.start_date,datetime.min.time(),tzinfo=UTC);end_dt=datetime.combine(p.end_date,datetime.max.time(),tzinfo=UTC)
        blocking=list(self.session.scalars(select(PaymentReconciliationModel).where(PaymentReconciliationModel.tenant_id==self.tenant_id,PaymentReconciliationModel.status.in_(["open","partial","exception"]),PaymentReconciliationModel.created_at>=start_dt,PaymentReconciliationModel.created_at<=end_dt)))
        pending=list(self.session.scalars(select(AccountingAdjustmentModel).where(AccountingAdjustmentModel.tenant_id==self.tenant_id,AccountingAdjustmentModel.status==AdjustmentStatus.PENDING_APPROVAL.value,AccountingAdjustmentModel.created_at>=start_dt,AccountingAdjustmentModel.created_at<=end_dt)))
        financial_exceptions=list(self.session.scalars(select(FinancialReconciliationExceptionModel).where(FinancialReconciliationExceptionModel.tenant_id==self.tenant_id,FinancialReconciliationExceptionModel.status=="open",FinancialReconciliationExceptionModel.created_at>=start_dt,FinancialReconciliationExceptionModel.created_at<=end_dt)))
        intents=list(self.session.scalars(select(PaymentIntentModel).where(PaymentIntentModel.tenant_id==self.tenant_id,PaymentIntentModel.created_at>=start_dt,PaymentIntentModel.created_at<=end_dt,PaymentIntentModel.status.in_(["ready_for_handoff","submitted","settled","void_pending"]))))
        unreconciled=[i for i in intents if (self.repo.reconciliation(i.payment_intent_id) is None or self.repo.reconciliation(i.payment_intent_id).status not in {"reconciled","returned"})]
        if blocking or pending or financial_exceptions or unreconciled:raise ReviewConflictError("accounting period close blocked by unresolved reconciliation, financial exception, unreconciled payment intent, or pending adjustment")
        journals=list(self.session.scalars(select(LedgerJournalModel).where(LedgerJournalModel.tenant_id==self.tenant_id,LedgerJournalModel.period_id==p.period_id)))
        debits=sum((_money(j.total_debits) for j in journals),Decimal("0.00"));credits=sum((_money(j.total_credits) for j in journals),Decimal("0.00"))
        if debits!=credits:raise ReviewConflictError("accounting period is not balanced")
        p.close_summary={"journal_count":len(journals),"total_debits":str(debits),"total_credits":str(credits),"blocking_reconciliations":0,"open_financial_exceptions":0,"unreconciled_payment_intents":0,"pending_adjustments":0,"rationale":rationale};p.close_sha256=_sha({"period_id":p.period_id,"period_key":p.period_key,"summary":p.close_summary,"journals":[j.journal_sha256 for j in journals],"controller":controller_user_id});p.status=AccountingPeriodStatus.CLOSED.value;p.lock_version+=1;p.closed_by_user_id=controller_user_id;p.closed_at=_now();self._emit(None, "accounting.period.closed","accounting_period",p.period_id,{"period_id":p.period_id,"status":"closed"},trace_id);return p
    def claim_snapshot(self,claim_id):
        intents=self.fin.intents(claim_id);recons=[self.repo.reconciliation(x.payment_intent_id) for x in intents];journals=self.repo.journals(claim_id);return {
            "claim_id":claim_id,"authority":ACCOUNTING_AUTHORITY,
            "payment_intents":[{"payment_intent_id":x.payment_intent_id,"amount":str(x.amount),"currency":x.currency,"status":x.status,"payee_ref":x.payee_ref,"external_instruction_id":x.external_instruction_id} for x in intents],
            "reconciliations":[{"reconciliation_id":r.reconciliation_id,"payment_intent_id":r.payment_intent_id,"expected_amount":str(r.expected_amount),"era_total":str(r.era_total),"eft_total":str(r.eft_total),"matched_amount":str(r.matched_amount),"unmatched_amount":str(r.unmatched_amount),"reference_match":r.reference_match,"status":r.status,"reconciliation_sha256":r.reconciliation_sha256,"journal_id":r.journal_id} for r in recons if r],
            "journals":[{"journal_id":j.journal_id,"period_id":j.period_id,"journal_type":j.journal_type,"source_type":j.source_type,"source_id":j.source_id,"currency":j.currency,"total_debits":str(j.total_debits),"total_credits":str(j.total_credits),"previous_journal_sha256":j.previous_journal_sha256,"journal_sha256":j.journal_sha256,"posted_by_actor_type":j.posted_by_actor_type,"posted_by_actor_id":j.posted_by_actor_id,"entries":[{"entry_id":e.entry_id,"sequence":e.entry_sequence,"account_code":e.account_code,"direction":e.direction,"amount":str(e.amount),"currency":e.currency,"memo":e.memo} for e in self.repo.entries(j.journal_id)]} for j in journals],
            "returns":[{"return_id":r.return_id,"payment_intent_id":r.payment_intent_id,"return_reference":r.return_reference,"return_code":r.return_code,"amount":str(r.amount),"status":r.status,"journal_id":r.journal_id} for i in intents for r in self.repo.returns(i.payment_intent_id)],
            "adjustments":[{"adjustment_id":a.adjustment_id,"payment_intent_id":a.payment_intent_id,"adjustment_type":a.adjustment_type,"amount":str(a.amount),"status":a.status,"requested_by_user_id":a.requested_by_user_id,"approved_by_user_id":a.approved_by_user_id,"journal_id":a.journal_id} for a in self.repo.adjustments(claim_id)],
            "provider_remittance":[{"payment_intent_id":s.payment_intent_id,"provider_ref":s.provider_ref,"status":s.status,"remitted_amount":str(s.remitted_amount),"latest_era_reference":s.latest_era_reference,"latest_eft_reference":s.latest_eft_reference} for i in intents if (s:=self.repo.remittance_status(i.payment_intent_id))],
            "aging_queue":[{"queue_id":q.queue_id,"payment_intent_id":q.payment_intent_id,"status":q.status,"age_days":q.age_days,"aging_bucket":q.aging_bucket,"priority":q.priority,"exception_codes":q.exception_codes} for q in self.repo.queue(claim_id)],
            "periods":[{"period_id":p.period_id,"period_key":p.period_key,"status":p.status,"lock_version":p.lock_version,"close_summary":p.close_summary,"close_sha256":p.close_sha256,"closed_by_user_id":p.closed_by_user_id} for p in list(self.session.scalars(select(AccountingPeriodModel).where(AccountingPeriodModel.tenant_id==self.tenant_id).order_by(AccountingPeriodModel.start_date)))],
            "traceability":self.traceability(claim_id),
        }
    def traceability(self,claim_id):
        intents=self.fin.intents(claim_id);nodes=[];edges=[]
        for i in intents:
            p=self.fin.packet(i.packet_id);nodes.extend([{"id":p.decision_history_sha256,"type":"controlling_human_decision_hash"},{"id":p.packet_id,"type":"human_authorized_financial_packet","sha256":p.authorized_payload_sha256},{"id":i.payment_intent_id,"type":"financial_instruction","status":i.status}]);edges.extend([{"from":p.decision_history_sha256,"to":p.packet_id,"relation":"authorized_financial_basis"},{"from":p.packet_id,"to":i.payment_intent_id,"relation":"stages_instruction"}])
            for se in self.fin.settlements(i.payment_intent_id):
                nodes.append({"id":se.settlement_event_id,"type":"external_settlement_status","status":se.status,"external_reference":se.external_reference,"payload_sha256":se.payload_sha256});edges.append({"from":i.payment_intent_id,"to":se.settlement_event_id,"relation":"external_settlement_status"})
            r=self.repo.reconciliation(i.payment_intent_id)
            if r:
                nodes.append({"id":r.reconciliation_id,"type":"era_eft_reconciliation","sha256":r.reconciliation_sha256,"status":r.status});edges.append({"from":i.payment_intent_id,"to":r.reconciliation_id,"relation":"era_eft_correlated_by"})
                if r.journal_id:edges.append({"from":r.reconciliation_id,"to":r.journal_id,"relation":"posts_balanced_journal"})
        periods={}
        for j in self.repo.journals(claim_id):
            nodes.append({"id":j.journal_id,"type":"immutable_ledger_journal","sha256":j.journal_sha256,"period_id":j.period_id});p=self.repo.period(j.period_id)
            if p and p.period_id not in periods:periods[p.period_id]=p;nodes.append({"id":p.period_id,"type":"accounting_period","status":p.status,"close_sha256":p.close_sha256});edges.append({"from":j.journal_id,"to":p.period_id,"relation":"posted_in_accounting_period"})
        return {"nodes":nodes,"edges":edges,"human_decision_to_financial_authorization_to_remittance_to_settlement_to_accounting_close":True,"automatic_fund_movement":False}
