from __future__ import annotations
import hashlib, json, math, re
from collections import Counter, defaultdict
from datetime import UTC, datetime
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from app.domain.financial_intelligence import FINANCIAL_INTELLIGENCE_AUTHORITY
from app.models.claims import ClaimModel
from app.models.financial_handoff import FinancialAuthorizationPacketModel, PaymentIntentModel, FinancialReconciliationExceptionModel
from app.models.accounting_ledger import AccountingPeriodModel, LedgerJournalModel, PaymentReconciliationModel, ReturnedPaymentModel, AccountingAdjustmentModel, ERARecordModel, AccountingReconciliationQueueModel
from app.models.financial_intelligence import ClaimReserveSnapshotModel, FinancialAnalyticsSnapshotModel, FinancialAnomalyInvestigationModel, FinancialCopilotRunModel
from app.repositories.financial_handoff import FinancialHandoffRepository
from app.repositories.accounting_ledger import AccountingLedgerRepository
from app.repositories.financial_intelligence import FinancialIntelligenceRepository
from app.repositories.tenancy import MembershipRepository
from app.observability.metrics import record_financial_intelligence, record_tokens
from app.services.review_workbench import ReviewConflictError

def _now(): return datetime.now(UTC)
def _money(v): return Decimal(str(v or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
def _canon(v): return json.dumps(v, sort_keys=True, separators=(",",":"), default=str)
def _sha(v): return hashlib.sha256((v if isinstance(v,str) else _canon(v)).encode()).hexdigest()
def _tokens(v): return re.findall(r"[a-z0-9_]+", str(v).lower())
def _severity(score:int)->str:
    if score>=80:return "critical"
    if score>=60:return "high"
    if score>=35:return "medium"
    return "low"


class FinancialCopilotSynthesis(BaseModel):
    answer: str = Field(min_length=1, max_length=6000)
    cited_ids: list[str] = Field(default_factory=list, max_length=25)
    recommendations: list[str] = Field(default_factory=list, max_length=8)

class FinancialIntelligenceService:
    """Read-only financial/accounting intelligence over Release 40/41 governed source records.

    The service may persist immutable derived analytics/citation snapshots only. It contains no method that
    edits journals, payment authorizations, reserve source-of-truth records, accounting periods, adjudication,
    settlement instructions, or movement of funds.
    """
    ALLOWED_ROLES={"finance_operator","finance_analyst","finance_approver","accounting_controller","auditor","tenant_admin"}
    def __init__(self, session:Session, tenant_id:str, *, model_client=None, copilot_model:str="gpt-5.6-terra"):
        self.session=session; self.tenant_id=tenant_id; self.fin=FinancialHandoffRepository(session,tenant_id); self.acct=AccountingLedgerRepository(session,tenant_id); self.repo=FinancialIntelligenceRepository(session,tenant_id);self.model_client=model_client;self.copilot_model=copilot_model
    def _require_reader(self,user_id:str):
        m=MembershipRepository(self.session,self.tenant_id).get_by_user(user_id)
        if m is None or m.status!="active" or m.role not in self.ALLOWED_ROLES: raise ReviewConflictError("human finance/accounting/audit read membership required")
        return m
    def _claim(self,claim_id):
        c=self.session.scalar(select(ClaimModel).where(ClaimModel.tenant_id==self.tenant_id,ClaimModel.claim_id==claim_id))
        if c is None: raise LookupError("claim not found")
        return c
    def _authorized_packet(self,claim_id):
        return self.session.scalar(select(FinancialAuthorizationPacketModel).where(FinancialAuthorizationPacketModel.tenant_id==self.tenant_id,FinancialAuthorizationPacketModel.claim_id==claim_id,FinancialAuthorizationPacketModel.status=="authorized").order_by(FinancialAuthorizationPacketModel.packet_version.desc()).limit(1))
    def _source_rows(self,claim_id=None):
        claim_filter=[] if claim_id is None else [PaymentIntentModel.claim_id==claim_id]
        intents=list(self.session.scalars(select(PaymentIntentModel).where(PaymentIntentModel.tenant_id==self.tenant_id,*claim_filter).order_by(PaymentIntentModel.created_at)))
        intent_ids=[x.payment_intent_id for x in intents]
        recons=[] if not intent_ids else list(self.session.scalars(select(PaymentReconciliationModel).where(PaymentReconciliationModel.tenant_id==self.tenant_id,PaymentReconciliationModel.payment_intent_id.in_(intent_ids))))
        returns=[] if not intent_ids else list(self.session.scalars(select(ReturnedPaymentModel).where(ReturnedPaymentModel.tenant_id==self.tenant_id,ReturnedPaymentModel.payment_intent_id.in_(intent_ids))))
        adjustments=list(self.session.scalars(select(AccountingAdjustmentModel).where(AccountingAdjustmentModel.tenant_id==self.tenant_id,*([] if claim_id is None else [AccountingAdjustmentModel.claim_id==claim_id]))))
        fin_ex=list(self.session.scalars(select(FinancialReconciliationExceptionModel).where(FinancialReconciliationExceptionModel.tenant_id==self.tenant_id,*([] if claim_id is None else [FinancialReconciliationExceptionModel.claim_id==claim_id]))))
        queues=list(self.session.scalars(select(AccountingReconciliationQueueModel).where(AccountingReconciliationQueueModel.tenant_id==self.tenant_id,*([] if claim_id is None else [AccountingReconciliationQueueModel.claim_id==claim_id]))))
        journals=list(self.session.scalars(select(LedgerJournalModel).where(LedgerJournalModel.tenant_id==self.tenant_id,*([] if claim_id is None else [LedgerJournalModel.claim_id==claim_id])).order_by(LedgerJournalModel.created_at)))
        eras=[] if not intent_ids else list(self.session.scalars(select(ERARecordModel).where(ERARecordModel.tenant_id==self.tenant_id,ERARecordModel.payment_intent_id.in_(intent_ids))))
        return intents,recons,returns,adjustments,fin_ex,queues,journals,eras
    def _watermark(self,claim_id=None):
        intents,recons,returns,adjustments,fin_ex,queues,journals,eras=self._source_rows(claim_id)
        packets=list(self.session.scalars(select(FinancialAuthorizationPacketModel).where(FinancialAuthorizationPacketModel.tenant_id==self.tenant_id,*([] if claim_id is None else [FinancialAuthorizationPacketModel.claim_id==claim_id])).order_by(FinancialAuthorizationPacketModel.claim_id,FinancialAuthorizationPacketModel.packet_version)))
        payload={"packets":[[p.packet_id,p.authorized_payload_sha256,p.decision_history_sha256,p.status,str(p.approved_amount)] for p in packets],"intents":[[i.payment_intent_id,i.status,str(i.amount),i.payment_fingerprint] for i in intents],"reconciliations":[[r.reconciliation_id,r.status,str(r.matched_amount),r.reconciliation_sha256] for r in recons],"returns":[[r.return_id,str(r.amount),r.status] for r in returns],"adjustments":[[a.adjustment_id,a.adjustment_type,str(a.amount),a.status] for a in adjustments],"exceptions":[[e.exception_id,e.exception_type,e.status] for e in fin_ex],"queues":[[q.queue_id,q.status,q.age_days,q.priority] for q in queues],"journals":[[j.journal_id,j.journal_sha256] for j in journals],"eras":[[e.era_id,e.provider_ref,str(e.paid_amount),e.payload_sha256] for e in eras]}
        return _sha(payload)
    def _claim_metrics(self,claim_id):
        claim=self._claim(claim_id); packet=self._authorized_packet(claim_id);intents,recons,returns,adjustments,fin_ex,queues,journals,eras=self._source_rows(claim_id)
        approved=_money(packet.approved_amount if packet else 0); incurred=approved
        reconciled=sum((_money(r.matched_amount) for r in recons if r.status in {"reconciled","returned"}),Decimal("0.00"))
        returned=sum((_money(r.amount) for r in returns),Decimal("0.00"));net_paid=max(Decimal("0.00"),reconciled-returned)
        reserve=max(Decimal("0.00"),incurred-net_paid)
        prior=self.repo.latest_reserve(claim_id);prior_reserve=_money(prior.outstanding_reserve if prior else reserve);variance=reserve-prior_reserve
        open_ex=[x for x in fin_ex if x.status=="open"];recon_status=Counter(r.status for r in recons);aging_max=max([q.age_days for q in queues if q.status!="closed"] or [0]);recoupments=[a for a in adjustments if a.adjustment_type=="recoupment"];open_recoup=[a for a in recoupments if a.status!="posted"]
        fingerprint_counts=Counter(i.payment_fingerprint for i in intents);duplicate_groups=sum(1 for n in fingerprint_counts.values() if n>1)
        overpayment=max(Decimal("0.00"),net_paid-approved)
        score=0;factors=[]
        def add(points,code,detail):
            nonlocal score;score+=points;factors.append({"factor":code,"points":points,"detail":detail})
        if duplicate_groups:add(60,"duplicate_payment_fingerprint",{"groups":duplicate_groups})
        if overpayment>0:add(50,"net_paid_exceeds_approved",{"overpayment":str(overpayment)})
        if open_ex:add(min(50,25*len(open_ex)),"open_financial_reconciliation_exception",{"count":len(open_ex)})
        if recon_status.get("exception",0):add(30,"era_eft_reconciliation_exception",{"count":recon_status["exception"]})
        if recon_status.get("partial",0):add(15,"partial_reconciliation",{"count":recon_status["partial"]})
        if returned>0:add(20,"returned_payment",{"amount":str(returned)})
        if aging_max>30:add(25,"reconciliation_aging_31_plus",{"days":aging_max})
        if open_recoup:add(15,"open_recoupment",{"count":len(open_recoup)})
        score=min(score,100)
        adequacy=100 if reserve>=max(Decimal("0"),approved-net_paid) else max(0,int((reserve/max(Decimal("0.01"),approved-net_paid))*100))
        citations=[]
        if packet:citations.append({"citation_id":f"financial_packet:{packet.packet_id}","type":"financial_authorization_packet","sha256":packet.authorized_payload_sha256,"claim_id":claim_id})
        citations += [{"citation_id":f"reconciliation:{r.reconciliation_id}","type":"era_eft_reconciliation","sha256":r.reconciliation_sha256,"status":r.status,"claim_id":claim_id} for r in recons]
        citations += [{"citation_id":f"journal:{j.journal_id}","type":"immutable_ledger_journal","sha256":j.journal_sha256,"claim_id":claim_id} for j in journals]
        citations += [{"citation_id":f"financial_exception:{e.exception_id}","type":"financial_exception","status":e.status,"claim_id":claim_id} for e in open_ex]
        metrics={"claim_total":str(_money(claim.total_amount)),"approved_incurred":str(incurred),"net_paid":str(net_paid),"outstanding_reserve":str(reserve),"reserve_variance":str(variance),"reserve_adequacy_score":adequacy,"paid_to_incurred_ratio":0.0 if incurred==0 else round(float(net_paid/incurred),4),"financial_leakage_exposure":str(overpayment+returned+sum((_money(a.amount) for a in recoupments if a.status=="posted"),Decimal("0"))),"overpayment_exposure":str(overpayment),"duplicate_payment_groups":duplicate_groups,"open_financial_exceptions":len(open_ex),"reconciliation_anomaly_score":score,"reconciliation_anomaly_severity":_severity(score),"max_reconciliation_age_days":aging_max,"recoupment_total":str(sum((_money(a.amount) for a in recoupments),Decimal("0"))),"open_recoupment_count":len(open_recoup)}
        return metrics,factors,citations,packet
    def claim_analytics(self,claim_id,*,persist=True):
        metrics,factors,citations,packet=self._claim_metrics(claim_id);watermark=self._watermark(claim_id)
        if persist:
            existing=self.repo.reserve_by_watermark(claim_id,watermark)
            if existing is None:
                prior=self.repo.latest_reserve(claim_id);prior_amt=_money(prior.outstanding_reserve if prior else metrics["outstanding_reserve"])
                reserve_payload={"claim_id":claim_id,"decision_history_sha256":None if packet is None else packet.decision_history_sha256,"metrics":metrics,"source_refs":citations,"watermark":watermark}
                self.repo.add(ClaimReserveSnapshotModel(reserve_snapshot_id=f"reserve_{uuid4().hex}",tenant_id=self.tenant_id,claim_id=claim_id,decision_history_sha256=None if packet is None else packet.decision_history_sha256,currency="USD" if packet is None else packet.currency,incurred_amount=_money(metrics["approved_incurred"]),approved_amount=_money(metrics["approved_incurred"]),net_paid_amount=_money(metrics["net_paid"]),outstanding_reserve=_money(metrics["outstanding_reserve"]),prior_outstanding_reserve=prior_amt,reserve_variance=_money(metrics["outstanding_reserve"])-prior_amt,adequacy_score=int(metrics["reserve_adequacy_score"]),source_refs=citations,source_watermark_sha256=watermark,payload_sha256=_sha(reserve_payload),created_at=_now()))
            snap=self.repo.analytics_by_watermark("claim",claim_id,watermark)
            if snap is None:
                snap_payload={"scope":"claim","claim_id":claim_id,"metrics":metrics,"anomalies":factors,"citations":citations,"watermark":watermark}
                self.repo.add(FinancialAnalyticsSnapshotModel(snapshot_id=f"finsnap_{uuid4().hex}",tenant_id=self.tenant_id,scope_type="claim",scope_id=claim_id,metrics=metrics,anomalies=factors,citations=citations,source_watermark_sha256=watermark,payload_sha256=_sha(snap_payload),created_by_actor_type="deterministic_read_only_analytics",created_at=_now()))
        record_financial_intelligence(metric="claim_anomaly_score",value=float(metrics["reconciliation_anomaly_score"]),attributes={"tenant_id":self.tenant_id,"claim_id":claim_id,"severity":metrics["reconciliation_anomaly_severity"]})
        return {"claim_id":claim_id,"authority":FINANCIAL_INTELLIGENCE_AUTHORITY,"metrics":metrics,"anomaly_factors":factors,"citations":citations,"source_watermark_sha256":watermark,"reserve_history":[{"reserve_snapshot_id":r.reserve_snapshot_id,"outstanding_reserve":str(r.outstanding_reserve),"reserve_variance":str(r.reserve_variance),"adequacy_score":r.adequacy_score,"created_at":r.created_at.isoformat()} for r in self.repo.reserve_history(claim_id)]}
    def _period_readiness(self):
        rows=[]
        periods=list(self.session.scalars(select(AccountingPeriodModel).where(AccountingPeriodModel.tenant_id==self.tenant_id).order_by(AccountingPeriodModel.start_date)))
        for p in periods:
            if p.status=="closed": rows.append({"period_id":p.period_id,"period_key":p.period_key,"status":p.status,"readiness_score":100,"blockers":[],"close_sha256":p.close_sha256});continue
            start_dt=datetime.combine(p.start_date,datetime.min.time(),tzinfo=UTC);end_dt=datetime.combine(p.end_date,datetime.max.time(),tzinfo=UTC);blockers=[]
            recons=list(self.session.scalars(select(PaymentReconciliationModel).where(PaymentReconciliationModel.tenant_id==self.tenant_id,PaymentReconciliationModel.status.in_(["open","partial","exception"]),PaymentReconciliationModel.created_at>=start_dt,PaymentReconciliationModel.created_at<=end_dt)))
            if recons:blockers.append({"code":"open_reconciliation","count":len(recons),"weight":30})
            fin_ex=list(self.session.scalars(select(FinancialReconciliationExceptionModel).where(FinancialReconciliationExceptionModel.tenant_id==self.tenant_id,FinancialReconciliationExceptionModel.status=="open",FinancialReconciliationExceptionModel.created_at>=start_dt,FinancialReconciliationExceptionModel.created_at<=end_dt)))
            if fin_ex:blockers.append({"code":"open_financial_exception","count":len(fin_ex),"weight":30})
            adj=list(self.session.scalars(select(AccountingAdjustmentModel).where(AccountingAdjustmentModel.tenant_id==self.tenant_id,AccountingAdjustmentModel.status=="pending_approval",AccountingAdjustmentModel.created_at>=start_dt,AccountingAdjustmentModel.created_at<=end_dt)))
            if adj:blockers.append({"code":"pending_adjustment","count":len(adj),"weight":20})
            intents=list(self.session.scalars(select(PaymentIntentModel).where(PaymentIntentModel.tenant_id==self.tenant_id,PaymentIntentModel.created_at>=start_dt,PaymentIntentModel.created_at<=end_dt,PaymentIntentModel.status.in_(["ready_for_handoff","submitted","settled","void_pending"]))))
            unreconciled=[i for i in intents if self.acct.reconciliation(i.payment_intent_id) is None or self.acct.reconciliation(i.payment_intent_id).status not in {"reconciled","returned"}]
            if unreconciled:blockers.append({"code":"unreconciled_payment_intent","count":len(unreconciled),"weight":30})
            journals=list(self.session.scalars(select(LedgerJournalModel).where(LedgerJournalModel.tenant_id==self.tenant_id,LedgerJournalModel.period_id==p.period_id)))
            unbalanced=[j for j in journals if _money(j.total_debits)!=_money(j.total_credits)]
            if unbalanced:blockers.append({"code":"unbalanced_journal","count":len(unbalanced),"weight":100})
            score=max(0,100-sum(min(100,b["weight"]*b["count"]) for b in blockers));rows.append({"period_id":p.period_id,"period_key":p.period_key,"status":p.status,"readiness_score":score,"blockers":blockers,"close_sha256":p.close_sha256})
        return rows
    def _provider_patterns(self):
        eras=list(self.session.scalars(select(ERARecordModel).where(ERARecordModel.tenant_id==self.tenant_id)))
        intents={i.payment_intent_id:i for i in self.session.scalars(select(PaymentIntentModel).where(PaymentIntentModel.tenant_id==self.tenant_id))}
        returns=list(self.session.scalars(select(ReturnedPaymentModel).where(ReturnedPaymentModel.tenant_id==self.tenant_id)))
        fin_ex=list(self.session.scalars(select(FinancialReconciliationExceptionModel).where(FinancialReconciliationExceptionModel.tenant_id==self.tenant_id,FinancialReconciliationExceptionModel.status=="open")))
        recoups=list(self.session.scalars(select(AccountingAdjustmentModel).where(AccountingAdjustmentModel.tenant_id==self.tenant_id,AccountingAdjustmentModel.adjustment_type=="recoupment")))
        by=defaultdict(lambda:{"era_total":Decimal("0"),"era_count":0,"intent_ids":set()})
        for e in eras:by[e.provider_ref]["era_total"]+=_money(e.paid_amount);by[e.provider_ref]["era_count"]+=1;by[e.provider_ref]["intent_ids"].add(e.payment_intent_id)
        out=[]
        for provider,d in by.items():
            ids=d["intent_ids"];ret=sum((_money(x.amount) for x in returns if x.payment_intent_id in ids),Decimal("0"));exc=sum(1 for x in fin_ex if x.payment_intent_id in ids);rec=sum((_money(x.amount) for x in recoups if x.payment_intent_id in ids),Decimal("0"));score=min(100,(25 if ret else 0)+min(40,20*exc)+(20 if rec else 0))
            out.append({"provider_ref":provider,"remitted_total":str(d["era_total"]),"era_count":d["era_count"],"payment_intent_count":len(ids),"returned_amount":str(ret),"open_exception_count":exc,"recoupment_amount":str(rec),"pattern_risk_score":score,"severity":_severity(score)})
        return sorted(out,key=lambda x:(-x["pattern_risk_score"],x["provider_ref"]))
    def portfolio(self,user_id,*,persist=True):
        self._require_reader(user_id);return self._portfolio(persist=persist)
    def portfolio_system(self,*,persist=True):
        """Background-safe read-only analytics refresh; no source financial/accounting mutations."""
        return self._portfolio(persist=persist)
    def _portfolio(self,*,persist=True):
        claims=list(self.session.scalars(select(ClaimModel).where(ClaimModel.tenant_id==self.tenant_id).order_by(ClaimModel.claim_id)))
        claim_rows=[]
        for c in claims:
            try:claim_rows.append(self.claim_analytics(c.claim_id,persist=persist))
            except (LookupError,ReviewConflictError):continue
        incurred=sum((_money(x["metrics"]["approved_incurred"]) for x in claim_rows),Decimal("0"));paid=sum((_money(x["metrics"]["net_paid"]) for x in claim_rows),Decimal("0"));reserve=sum((_money(x["metrics"]["outstanding_reserve"]) for x in claim_rows),Decimal("0"));leakage=sum((_money(x["metrics"]["financial_leakage_exposure"]) for x in claim_rows),Decimal("0"));high=sum(1 for x in claim_rows if x["metrics"]["reconciliation_anomaly_score"]>=60)
        recoups=list(self.session.scalars(select(AccountingAdjustmentModel).where(AccountingAdjustmentModel.tenant_id==self.tenant_id,AccountingAdjustmentModel.adjustment_type=="recoupment")))
        now=_now();recoup_aging=[{"adjustment_id":a.adjustment_id,"claim_id":a.claim_id,"amount":str(a.amount),"status":a.status,"age_days":max(0,(now-(a.created_at if a.created_at.tzinfo else a.created_at.replace(tzinfo=UTC))).days)} for a in recoups]
        readiness=self._period_readiness();provider=self._provider_patterns();control_exceptions=[{"period_id":p["period_id"],"period_key":p["period_key"],**b} for p in readiness for b in p["blockers"]]
        metrics={"claims_analyzed":len(claim_rows),"incurred_amount":str(incurred),"net_paid_amount":str(paid),"outstanding_reserve":str(reserve),"paid_to_incurred_ratio":0.0 if incurred==0 else round(float(paid/incurred),4),"reserve_to_incurred_ratio":0.0 if incurred==0 else round(float(reserve/incurred),4),"financial_leakage_exposure":str(leakage),"high_risk_claims":high,"open_recoupments":sum(1 for x in recoups if x.status!="posted"),"accounting_control_exception_count":len(control_exceptions),"period_close_readiness_average":0 if not readiness else round(sum(x["readiness_score"] for x in readiness)/len(readiness),1)}
        watermark=self._watermark();citations=[c for x in claim_rows for c in x["citations"]][:500];anomalies=[{"claim_id":x["claim_id"],"score":x["metrics"]["reconciliation_anomaly_score"],"severity":x["metrics"]["reconciliation_anomaly_severity"],"factors":x["anomaly_factors"]} for x in claim_rows if x["metrics"]["reconciliation_anomaly_score"]>0]
        if persist and self.repo.analytics_by_watermark("portfolio","portfolio",watermark) is None:
            payload={"metrics":metrics,"provider_patterns":provider,"period_close_readiness":readiness,"recoupment_aging":recoup_aging,"anomalies":anomalies,"watermark":watermark}
            self.repo.add(FinancialAnalyticsSnapshotModel(snapshot_id=f"finsnap_{uuid4().hex}",tenant_id=self.tenant_id,scope_type="portfolio",scope_id="portfolio",metrics=metrics,anomalies=anomalies,citations=citations,source_watermark_sha256=watermark,payload_sha256=_sha(payload),created_by_actor_type="deterministic_read_only_analytics",created_at=_now()))
        record_financial_intelligence(metric="portfolio_leakage_exposure",value=float(leakage),attributes={"tenant_id":self.tenant_id});record_financial_intelligence(metric="period_close_readiness",value=float(metrics["period_close_readiness_average"]),attributes={"tenant_id":self.tenant_id})
        return {"authority":FINANCIAL_INTELLIGENCE_AUTHORITY,"kpis":metrics,"claims":[{"claim_id":x["claim_id"],**x["metrics"]} for x in claim_rows],"provider_patterns":provider,"recoupment_aging":sorted(recoup_aging,key=lambda x:-x["age_days"]),"accounting_control_exceptions":control_exceptions,"period_close_readiness":readiness,"anomalies":sorted(anomalies,key=lambda x:-x["score"]),"source_watermark_sha256":watermark}
    def investigate(self,claim_id,user_id,anomaly_code):
        self._require_reader(user_id);data=self.claim_analytics(claim_id,persist=True);matched=[f for f in data["anomaly_factors"] if f["factor"]==anomaly_code]
        if not matched: raise LookupError("requested anomaly is not present in current governed source data")
        score=int(data["metrics"]["reconciliation_anomaly_score"]);recommendations=["Review the cited financial/accounting records with an authorized human finance analyst.","Resolve source reconciliation exceptions through the governed Release 40/41 workflows; do not edit ledger history."]
        explanation=f"Deterministic read-only investigation for {anomaly_code}. Score {score}/100 is derived from governed reconciliation, return, aging, duplicate and overpayment indicators; it does not change payment or accounting state."
        payload={"claim_id":claim_id,"anomaly_code":anomaly_code,"score":score,"factors":matched,"citations":data["citations"],"recommendations":recommendations,"authority":"none"}
        row=self.repo.add(FinancialAnomalyInvestigationModel(investigation_id=f"fininv_{uuid4().hex}",tenant_id=self.tenant_id,claim_id=claim_id,anomaly_code=anomaly_code,anomaly_score=score,severity=_severity(score),explanation=explanation,factors=matched,evidence_citations=data["citations"],recommendations=recommendations,adjudication_authority="none",accounting_authority="none",fund_movement_authority="none",payload_sha256=_sha(payload),created_at=_now()))
        return {"investigation_id":row.investigation_id,"claim_id":claim_id,"anomaly_code":anomaly_code,"anomaly_score":score,"severity":row.severity,"explanation":explanation,"factors":matched,"citations":data["citations"],"recommendations":recommendations,"authority":{"adjudication":"none","accounting":"none","fund_movement":"none"},"payload_sha256":row.payload_sha256}
    def _documents(self,claim_id=None):
        docs=[]
        claims=[self._claim(claim_id)] if claim_id else list(self.session.scalars(select(ClaimModel).where(ClaimModel.tenant_id==self.tenant_id)))
        for c in claims:
            try:d=self.claim_analytics(c.claim_id,persist=False)
            except Exception:continue
            docs.append({"citation_id":f"analytics:claim:{c.claim_id}","claim_id":c.claim_id,"type":"claim_financial_analytics","text":_canon(d["metrics"]),"sha256":d["source_watermark_sha256"]})
            for cit in d["citations"]:docs.append({"citation_id":cit["citation_id"],"claim_id":c.claim_id,"type":cit["type"],"text":_canon(cit),"sha256":cit.get("sha256")})
        for p in self._period_readiness():docs.append({"citation_id":f"accounting_period:{p['period_id']}","claim_id":None,"type":"accounting_period_readiness","text":_canon(p),"sha256":p.get("close_sha256")})
        return docs
    def copilot(self,user_id,query,*,claim_id=None,top_k=8):
        self._require_reader(user_id);docs=self._documents(claim_id);qt=Counter(_tokens(query));scored=[]
        for d in docs:
            dt=Counter(_tokens(d["text"]+" "+d["type"]));overlap=sum(min(n,dt[t]) for t,n in qt.items());score=overlap/(math.sqrt(max(1,sum(qt.values())))*math.sqrt(max(1,sum(dt.values()))));scored.append((score,d))
        chosen=[d for score,d in sorted(scored,key=lambda x:-x[0]) if score>0][:top_k]
        if not chosen:chosen=docs[:top_k]
        cites=[{"citation_id":d["citation_id"],"claim_id":d["claim_id"],"type":d["type"],"sha256":d["sha256"],"retrieval_score":round(next((s for s,x in scored if x is d),0.0),4)} for d in chosen]
        summary=[]
        if claim_id:
            data=self.claim_analytics(claim_id,persist=False);m=data["metrics"];summary=[f"Claim {claim_id} has approved/incurred {m['approved_incurred']}, net paid {m['net_paid']}, outstanding reserve {m['outstanding_reserve']}, and reconciliation anomaly score {m['reconciliation_anomaly_score']}/100."]
        else:
            p=self.portfolio(user_id,persist=False);k=p["kpis"];summary=[f"Portfolio incurred is {k['incurred_amount']}, net paid is {k['net_paid_amount']}, outstanding reserve is {k['outstanding_reserve']}, and detected leakage exposure is {k['financial_leakage_exposure']}."]
        fallback=" ".join(summary)+" Evidence was retrieved only from governed financial/accounting records."
        answer=fallback
        if self.model_client is not None and chosen:
            instructions=("You are a payer financial analytics copilot. Use only the supplied governed evidence. "
                          "Do not invent amounts or facts. Do not authorize, approve, post, close, adjudicate, or move funds. "
                          "Return concise analytical explanation and cite only citation_id values present in the evidence.")
            try:
                response=self.model_client.generate(model=self.copilot_model,instructions=instructions,input_text=_canon({"query":query,"evidence":chosen}),schema=FinancialCopilotSynthesis)
                parsed=response.parsed;allowed={d["citation_id"] for d in chosen}
                if not parsed.cited_ids or any(x not in allowed for x in parsed.cited_ids):raise ValueError("model citation set is not fully grounded in retrieved financial evidence")
                answer=parsed.answer.strip()
                if parsed.recommendations:answer += " Recommendations for authorized human review: " + "; ".join(parsed.recommendations)
                record_tokens(model=response.model,input_tokens=response.input_tokens,output_tokens=response.output_tokens)
            except Exception:
                answer=fallback
        answer += " This copilot is recommendation-only and cannot modify journals, reserves, payment authorization, accounting periods, adjudication outcomes, or funds."
        watermark=self._watermark(claim_id);payload={"query":query,"answer":answer,"citations":cites,"watermark":watermark,"authority":"none"}
        row=self.repo.add(FinancialCopilotRunModel(run_id=f"fincop_{uuid4().hex}",tenant_id=self.tenant_id,requested_by_user_id=user_id,query_text=query,answer_text=answer,citations=cites,retrieval_strategy="structured_ledger_hybrid_lexical_citation_retrieval_v1",source_watermark_sha256=watermark,adjudication_authority="none",accounting_authority="none",fund_movement_authority="none",payload_sha256=_sha(payload),created_at=_now()))
        record_financial_intelligence(metric="copilot_run",value=1,attributes={"tenant_id":self.tenant_id,"citation_count":len(cites)})
        return {"run_id":row.run_id,"answer":answer,"citations":cites,"retrieval_strategy":row.retrieval_strategy,"source_watermark_sha256":watermark,"authority":{"adjudication":"none","accounting":"none","fund_movement":"none"},"payload_sha256":row.payload_sha256}
