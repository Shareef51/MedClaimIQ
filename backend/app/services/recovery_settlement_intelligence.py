from __future__ import annotations
import hashlib,json,math,re
from collections import Counter,defaultdict
from datetime import UTC,date,datetime
from decimal import Decimal,ROUND_HALF_UP
from uuid import uuid4
from pydantic import BaseModel,Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.domain.recovery_settlement_intelligence import RECOVERY_SETTLEMENT_INTELLIGENCE_AUTHORITY
from app.domain.realtime import EventEnvelope,EventTopic
from app.models.accounting_ledger import AccountingPeriodModel,LedgerJournalModel
from app.models.recovery_settlement import (RecoverySettlementCaseModel,RecoverySettlementEvidenceModel,RecoveryLedgerCorrelationModel,RecoverySettlementExceptionModel,RecoveryCompletionCertificateModel,RecoverySettlementCorrespondenceModel)
from app.models.recovery_settlement_intelligence import *
from app.observability.metrics import record_recovery_settlement_intelligence,record_tokens
from app.realtime.events import enqueue_realtime_event
from app.repositories.recovery_settlement_intelligence import RecoverySettlementIntelligenceRepository
from app.repositories.tenancy import MembershipRepository
from app.services.review_workbench import ReviewConflictError

def _now():return datetime.now(UTC)
def _money(v):return Decimal(str(v or 0)).quantize(Decimal("0.01"),rounding=ROUND_HALF_UP)
def _canon(v):return json.dumps(v,sort_keys=True,separators=(",",":"),default=str)
def _sha(v):return hashlib.sha256((v if isinstance(v,str) else _canon(v)).encode()).hexdigest()
def _tokens(v):return re.findall(r"[a-z0-9_]+",str(v).lower())
def _aware(v):return v if v.tzinfo else v.replace(tzinfo=UTC)
def _bucket(days):return "0-2d" if days<=2 else "3-7d" if days<=7 else "8-30d" if days<=30 else "31+d"

class RecoverySettlementCopilotSynthesis(BaseModel):
    answer:str=Field(min_length=1,max_length=6000);cited_ids:list[str]=Field(default_factory=list,max_length=25);recommendations:list[str]=Field(default_factory=list,max_length=8)

class RecoverySettlementIntelligenceService:
    """Read-only intelligence over Release 47 settlement and Release 41 ledger state.

    Writes are limited to immutable derived statements, analytics snapshots, investigation observations,
    audit/report manifests, portal statement delivery provenance, and copilot provenance. This service has
    no source-state mutation, bank transaction, collection, payment authorization, journal posting, closeout
    certificate decision, or accounting-period close operation.
    """
    READ_ROLES={"finance_operator","finance_analyst","finance_approver","accounting_controller","auditor","tenant_admin"}
    PUBLISH_ROLES={"finance_analyst","finance_approver","tenant_admin"}
    def __init__(self,session:Session,tenant_id:str,*,model_client=None,copilot_model:str="gpt-5.6-terra"):
        self.session=session;self.tenant_id=tenant_id;self.repo=RecoverySettlementIntelligenceRepository(session,tenant_id);self.members=MembershipRepository(session,tenant_id);self.model_client=model_client;self.copilot_model=copilot_model
    def _membership(self,user_id):
        m=self.members.get_by_user(user_id)
        if m is None or m.status!="active":raise ReviewConflictError("active tenant membership required")
        return m
    def _reader(self,user_id):
        m=self._membership(user_id)
        if m.role not in self.READ_ROLES:raise ReviewConflictError("recovery settlement intelligence read membership required")
        return m
    def _publisher(self,user_id):
        m=self._membership(user_id)
        if m.role not in self.PUBLISH_ROLES:raise ReviewConflictError("human finance analyst/approver required to publish provider balance statement")
        return m
    def _cases(self,provider_id=None):
        q=select(RecoverySettlementCaseModel).where(RecoverySettlementCaseModel.tenant_id==self.tenant_id)
        if provider_id:q=q.where(RecoverySettlementCaseModel.provider_organization_id==provider_id)
        return list(self.session.scalars(q.order_by(RecoverySettlementCaseModel.created_at)))
    def _evidence(self,case_id):return list(self.session.scalars(select(RecoverySettlementEvidenceModel).where(RecoverySettlementEvidenceModel.tenant_id==self.tenant_id,RecoverySettlementEvidenceModel.settlement_case_id==case_id).order_by(RecoverySettlementEvidenceModel.installment_sequence)))
    def _correlations(self,case_id):return list(self.session.scalars(select(RecoveryLedgerCorrelationModel).where(RecoveryLedgerCorrelationModel.tenant_id==self.tenant_id,RecoveryLedgerCorrelationModel.settlement_case_id==case_id)))
    def _exceptions(self,case_id):return list(self.session.scalars(select(RecoverySettlementExceptionModel).where(RecoverySettlementExceptionModel.tenant_id==self.tenant_id,RecoverySettlementExceptionModel.settlement_case_id==case_id)))
    def _certificate(self,case_id):return self.session.scalar(select(RecoveryCompletionCertificateModel).where(RecoveryCompletionCertificateModel.tenant_id==self.tenant_id,RecoveryCompletionCertificateModel.settlement_case_id==case_id))
    def _source_rows(self,provider_id=None):
        rows=[]
        for c in self._cases(provider_id):
            rows.append({"type":"settlement_case","id":c.settlement_case_id,"target":str(c.target_amount),"verified":str(c.verified_amount),"remaining":str(c.remaining_amount),"status":c.status,"position_sha256":c.position_payload_sha256,"updated_at":c.updated_at})
            rows += [{"type":"settlement_evidence","id":x.settlement_evidence_id,"status":x.status,"amount":str(x.amount),"sha256":x.evidence_payload_sha256,"verified_at":x.verified_at} for x in self._evidence(c.settlement_case_id)]
            rows += [{"type":"ledger_correlation","id":x.correlation_id,"journal_id":x.journal_id,"amount":str(x.amount),"sha256":x.correlation_payload_sha256} for x in self._correlations(c.settlement_case_id)]
            rows += [{"type":"settlement_exception","id":x.exception_id,"code":x.exception_code,"status":x.status,"details":x.details} for x in self._exceptions(c.settlement_case_id)]
            cert=self._certificate(c.settlement_case_id)
            if cert:rows.append({"type":"completion_certificate","id":cert.certificate_id,"status":cert.status,"period_id":cert.accounting_period_id,"sha256":cert.payload_sha256,"certified_at":cert.certified_at})
        return rows
    def _watermark(self,provider_id=None):return _sha(self._source_rows(provider_id))
    def _case_metrics(self,c):
        now=_now();age=max(0,(now-_aware(c.created_at)).days);target=_money(c.target_amount);verified=_money(c.verified_amount);remaining=_money(c.remaining_amount);over=max(Decimal("0"),verified-target);under=max(Decimal("0"),target-verified)
        evidence=self._evidence(c.settlement_case_id);verified_e=[x for x in evidence if x.status=="verified"]
        offsets=sum((_money(x.amount) for x in verified_e if x.evidence_type=="recoupment_offset"),Decimal("0"));repayments=sum((_money(x.amount) for x in verified_e if x.evidence_type in {"bank_repayment","provider_remittance","refund_credit"}),Decimal("0"));exceptions=self._exceptions(c.settlement_case_id);open_exc=[x for x in exceptions if x.status=="open"];cert=self._certificate(c.settlement_case_id)
        score=100
        if remaining>0:score-=35
        if age>7 and remaining>0:score-=20
        if open_exc:score-=min(30,10*len(open_exc))
        if cert is None or cert.status!="certified":score-=15
        score=max(0,score)
        citations=[{"citation_id":f"recovery_settlement:{c.settlement_case_id}","type":"settlement_case","sha256":c.position_payload_sha256},{"citation_id":f"recovery_position:{c.position_version_id}","type":"recovery_position","sha256":c.position_payload_sha256}]
        citations += [{"citation_id":f"settlement_evidence:{x.settlement_evidence_id}","type":"settlement_evidence","sha256":x.evidence_payload_sha256} for x in evidence]
        citations += [{"citation_id":f"ledger_correlation:{x.correlation_id}","type":"ledger_correlation","sha256":x.correlation_payload_sha256,"journal_id":x.journal_id} for x in self._correlations(c.settlement_case_id)]
        if cert:citations.append({"citation_id":f"completion_certificate:{cert.certificate_id}","type":"completion_certificate","sha256":cert.payload_sha256,"period_id":cert.accounting_period_id})
        anomalies=[]
        if under>0:anomalies.append({"code":"under_recovery","severity":"high" if age>7 else "medium","amount":str(under),"age_days":age})
        if over>0:anomalies.append({"code":"over_recovery","severity":"critical","amount":str(over)})
        for x in open_exc:anomalies.append({"code":x.exception_code,"severity":x.severity,"details":x.details})
        return {"settlement_case_id":c.settlement_case_id,"claim_id":c.claim_id,"provider_organization_id":c.provider_organization_id,"currency":c.currency,"target_recovery":str(target),"verified_recovery":str(verified),"remaining_balance":str(remaining),"under_recovery_amount":str(under),"over_recovery_amount":str(over),"repayment_amount":str(repayments),"offset_amount":str(offsets),"age_days":age,"aging_bucket":_bucket(age),"status":c.status,"certified":bool(cert and cert.status=="certified"),"effectiveness_score":score,"anomalies":anomalies,"citations":citations}
    def provider_statement(self,provider_id,user_id=None,*,persist=True,system=False):
        if not system:self._reader(user_id)
        cases=self._cases(provider_id)
        if not cases:raise LookupError("provider has no recovery settlement cases")
        metrics=[self._case_metrics(c) for c in cases];currency=cases[0].currency
        if any(c.currency!=currency for c in cases):raise ReviewConflictError("provider balance statement cannot aggregate multiple currencies")
        target=sum((_money(x["target_recovery"]) for x in metrics),Decimal("0"));verified=sum((_money(x["verified_recovery"]) for x in metrics),Decimal("0"));remaining=sum((_money(x["remaining_balance"]) for x in metrics),Decimal("0"));under=sum((_money(x["under_recovery_amount"]) for x in metrics),Decimal("0"));over=sum((_money(x["over_recovery_amount"]) for x in metrics),Decimal("0"));aging=Counter(x["aging_bucket"] for x in metrics if _money(x["remaining_balance"])>0);watermark=self._watermark(provider_id)
        payload={"provider_organization_id":provider_id,"as_of_date":date.today().isoformat(),"currency":currency,"target_recovery":str(target),"verified_recovery":str(verified),"remaining_balance":str(remaining),"under_recovery_amount":str(under),"over_recovery_amount":str(over),"open_case_count":sum(not x["certified"] for x in metrics),"certified_case_count":sum(x["certified"] for x in metrics),"aging_summary":dict(aging),"case_lines":metrics,"source_watermark_sha256":watermark}
        row=self.repo.statement_by_watermark(provider_id,watermark)
        if persist and row is None:
            row=self.repo.add(ProviderRecoveryBalanceStatementModel(statement_id=f"prbs_{uuid4().hex}",tenant_id=self.tenant_id,provider_organization_id=provider_id,statement_version=self.repo.next_statement_version(provider_id),as_of_date=date.today(),currency=currency,target_recovery=target,verified_recovery=verified,remaining_balance=remaining,under_recovery_amount=under,over_recovery_amount=over,open_case_count=payload["open_case_count"],certified_case_count=payload["certified_case_count"],aging_summary=dict(aging),case_lines=metrics,source_refs=[c["citation_id"] for x in metrics for c in x["citations"]],source_watermark_sha256=watermark,payload_sha256=_sha(payload),created_by_actor_type="deterministic_read_only_worker" if system else "human_requested_read_only_intelligence",created_at=_now()))
            self._emit("recovery_settlement_intelligence.statement.generated",provider_id,row.statement_id,{"statement_version":row.statement_version,"remaining_balance":str(row.remaining_balance)})
        if row:payload|={"statement_id":row.statement_id,"statement_version":row.statement_version,"payload_sha256":row.payload_sha256,"created_at":row.created_at,"delivered":self.repo.delivery(row.statement_id) is not None,"history":[{"statement_id":h.statement_id,"statement_version":h.statement_version,"as_of_date":h.as_of_date,"target_recovery":str(h.target_recovery),"verified_recovery":str(h.verified_recovery),"remaining_balance":str(h.remaining_balance),"payload_sha256":h.payload_sha256,"delivered":self.repo.delivery(h.statement_id) is not None} for h in self.repo.statements(provider_id)]}
        record_recovery_settlement_intelligence(metric="provider_remaining_balance",value=float(remaining),attributes={"tenant_id":self.tenant_id,"provider_organization_id":provider_id})
        return {"authority":RECOVERY_SETTLEMENT_INTELLIGENCE_AUTHORITY,**payload}
    def portfolio(self,user_id=None,*,persist=True,system=False):
        if not system:self._reader(user_id)
        cases=self._cases();metrics=[self._case_metrics(c) for c in cases];providers=sorted({c.provider_organization_id for c in cases if c.provider_organization_id});provider_rows=[self.provider_statement(p,user_id,persist=persist,system=system) for p in providers]
        target=sum((_money(x["target_recovery"]) for x in metrics),Decimal("0"));verified=sum((_money(x["verified_recovery"]) for x in metrics),Decimal("0"));remaining=sum((_money(x["remaining_balance"]) for x in metrics),Decimal("0"));under=sum((_money(x["under_recovery_amount"]) for x in metrics),Decimal("0"));over=sum((_money(x["over_recovery_amount"]) for x in metrics),Decimal("0"));aging=Counter(x["aging_bucket"] for x in metrics if _money(x["remaining_balance"])>0);exceptions=[{**a,"settlement_case_id":x["settlement_case_id"],"provider_organization_id":x["provider_organization_id"]} for x in metrics for a in x["anomalies"]];watermark=self._watermark()
        currency_totals={}
        for cur in sorted({x["currency"] for x in metrics}):
            cm=[x for x in metrics if x["currency"]==cur];currency_totals[cur]={"target_recovery":str(sum((_money(x["target_recovery"]) for x in cm),Decimal("0"))),"verified_recovery":str(sum((_money(x["verified_recovery"]) for x in cm),Decimal("0"))),"remaining_balance":str(sum((_money(x["remaining_balance"]) for x in cm),Decimal("0")))}
        kpis={"settlement_cases":len(cases),"certified_cases":sum(x["certified"] for x in metrics),"open_cases":sum(not x["certified"] for x in metrics),"target_recovery":str(target),"verified_recovery":str(verified),"remaining_balance":str(remaining),"under_recovery_amount":str(under),"over_recovery_amount":str(over),"recovery_effectiveness_pct":0.0 if target==0 else round(float(verified/target*100),2),"open_exception_count":len(exceptions),"provider_count":len(providers),"currency_totals":currency_totals}
        if persist and self.repo.analytics_by_watermark("portfolio","portfolio",watermark) is None:
            payload={"kpis":kpis,"aging":dict(aging),"providers":[{"provider_organization_id":p["provider_organization_id"],"remaining_balance":p["remaining_balance"],"payload_sha256":p.get("payload_sha256")} for p in provider_rows],"source_watermark_sha256":watermark}
            self.repo.add(RecoverySettlementAnalyticsSnapshotModel(snapshot_id=f"rsis_{uuid4().hex}",tenant_id=self.tenant_id,scope_type="portfolio",scope_id="portfolio",metrics={**kpis,"aging":dict(aging)},anomalies=exceptions,citations=[c for x in metrics for c in x["citations"]][:1000],source_watermark_sha256=watermark,payload_sha256=_sha(payload),created_by_actor_type="deterministic_read_only_intelligence",created_at=_now()))
            self._emit("recovery_settlement_intelligence.analytics.refreshed","portfolio",f"rsis:{watermark[:16]}",{"cases":len(cases),"remaining_balance":str(remaining)})
        record_recovery_settlement_intelligence(metric="portfolio_recovery_effectiveness_pct",value=float(kpis["recovery_effectiveness_pct"]),attributes={"tenant_id":self.tenant_id});record_recovery_settlement_intelligence(metric="portfolio_remaining_balance",value=float(remaining),attributes={"tenant_id":self.tenant_id})
        return {"authority":RECOVERY_SETTLEMENT_INTELLIGENCE_AUTHORITY,"kpis":kpis,"aging":dict(aging),"providers":provider_rows,"cases":metrics,"settlement_exceptions":exceptions,"source_watermark_sha256":watermark}
    def accounting_closeout_report(self,period_id,user_id,*,persist=True):
        self._reader(user_id);period=self.session.scalar(select(AccountingPeriodModel).where(AccountingPeriodModel.tenant_id==self.tenant_id,AccountingPeriodModel.period_id==period_id))
        if period is None:raise LookupError("accounting period not found")
        certs=list(self.session.scalars(select(RecoveryCompletionCertificateModel).where(RecoveryCompletionCertificateModel.tenant_id==self.tenant_id,RecoveryCompletionCertificateModel.accounting_period_id==period_id)))
        rows=[]
        for cert in certs:
            c=self.session.get(RecoverySettlementCaseModel,cert.settlement_case_id)
            rows.append({"certificate_id":cert.certificate_id,"settlement_case_id":cert.settlement_case_id,"recovery_case_id":cert.recovery_case_id,"status":cert.status,"target_amount":str(cert.target_amount),"verified_amount":str(cert.verified_amount),"remaining_amount":str(cert.remaining_amount),"certificate_sha256":cert.payload_sha256,"position_sha256":c.position_payload_sha256 if c else None})
        watermark=_sha({"period_id":period_id,"period_status":period.status,"close_sha256":period.close_sha256,"certificates":rows})
        manifest={"report_type":"recovery_settlement_regulatory_closeout","period_id":period_id,"period_key":period.period_key,"period_status":period.status,"period_close_sha256":period.close_sha256,"certificate_count":len(rows),"certificates":rows,"total_verified":str(sum((_money(x["verified_amount"]) for x in rows),Decimal("0"))),"authority":"read_only_reporting","source_watermark_sha256":watermark}
        row=self.repo.report_by_watermark("accounting_period",period_id,watermark)
        if persist and row is None:
            row=self.repo.add(RecoveryCloseoutReportModel(report_id=f"rscr_{uuid4().hex}",tenant_id=self.tenant_id,report_scope="accounting_period",scope_id=period_id,report_version=self.repo.next_report_version("accounting_period",period_id),manifest=manifest,source_refs=[f"completion_certificate:{x['certificate_id']}" for x in rows]+[f"accounting_period:{period_id}"],source_watermark_sha256=watermark,manifest_sha256=_sha(manifest),created_by_actor_type="human_requested_read_only_reporting",created_at=_now()))
            self._emit("recovery_settlement_intelligence.closeout_report.generated",period_id,row.report_id,{"period_id":period_id,"certificate_count":len(rows)})
        return {**manifest,"report_id":row.report_id if row else None,"report_version":row.report_version if row else None,"manifest_sha256":row.manifest_sha256 if row else _sha(manifest)}
    def investigate_exception(self,case_id,user_id,exception_code):
        self._reader(user_id);c=self.session.scalar(select(RecoverySettlementCaseModel).where(RecoverySettlementCaseModel.tenant_id==self.tenant_id,RecoverySettlementCaseModel.settlement_case_id==case_id))
        if c is None:raise LookupError("settlement case not found")
        data=self._case_metrics(c);factors=[x for x in data["anomalies"] if x["code"]==exception_code]
        if not factors:raise LookupError("requested settlement anomaly is not present")
        severity=factors[0].get("severity","medium");recommendations=["Review the cited Release 47 settlement evidence and ledger correlations with an authorized human finance analyst.","Resolve any financial or accounting source exception only through the governed Release 40/41/47 human workflows; do not edit history from this intelligence layer."]
        explanation=f"Read-only settlement investigation for {exception_code}. It explains governed source evidence and does not alter balances, journals, payment instructions, closeout certificates, collections, or funds."
        payload={"case_id":case_id,"code":exception_code,"factors":factors,"citations":data["citations"],"authority":"none"}
        row=self.repo.add(RecoverySettlementExceptionInvestigationModel(investigation_id=f"rsei_{uuid4().hex}",tenant_id=self.tenant_id,settlement_case_id=case_id,exception_code=exception_code,severity=severity,explanation=explanation,factors=factors,citations=data["citations"],recommendations=recommendations,accounting_authority="none",fund_movement_authority="none",payload_sha256=_sha(payload),created_at=_now()))
        self._emit("recovery_settlement_intelligence.exception.investigated",case_id,row.investigation_id,{"exception_code":exception_code,"severity":severity})
        return {"investigation_id":row.investigation_id,"settlement_case_id":case_id,"exception_code":exception_code,"severity":severity,"explanation":explanation,"factors":factors,"citations":data["citations"],"recommendations":recommendations,"authority":{"accounting":"none","fund_movement":"none"},"payload_sha256":row.payload_sha256}
    def publish_statement(self,statement_id,user_id,*,idempotency_key):
        self._publisher(user_id);statement=self.repo.statement(statement_id)
        if statement is None:raise LookupError("provider balance statement not found")
        existing=self.repo.delivery(statement_id)
        if existing:return existing
        payload={"statement_id":statement_id,"provider_organization_id":statement.provider_organization_id,"statement_version":statement.statement_version,"statement_payload_sha256":statement.payload_sha256,"channel":"portal","released_by_user_id":user_id}
        row=self.repo.add(ProviderBalanceStatementDeliveryModel(delivery_id=f"prbsd_{uuid4().hex}",tenant_id=self.tenant_id,statement_id=statement_id,provider_organization_id=statement.provider_organization_id,channel="portal",released_by_user_id=user_id,delivery_payload_sha256=_sha(payload),idempotency_key=idempotency_key,delivered_at=_now()))
        self._emit("recovery_settlement_intelligence.statement.delivered",statement.provider_organization_id,row.delivery_id,{"statement_id":statement_id,"statement_version":statement.statement_version,"channel":"portal"})
        return row
    def provider_portal_statements(self,user_id):
        m=self._membership(user_id)
        if m.role!="provider" or not m.provider_organization_id:raise ReviewConflictError("provider membership required")
        out=[]
        for s in self.repo.statements(m.provider_organization_id):
            d=self.repo.delivery(s.statement_id)
            if d:out.append({"statement_id":s.statement_id,"statement_version":s.statement_version,"as_of_date":s.as_of_date,"currency":s.currency,"target_recovery":str(s.target_recovery),"verified_recovery":str(s.verified_recovery),"remaining_balance":str(s.remaining_balance),"under_recovery_amount":str(s.under_recovery_amount),"over_recovery_amount":str(s.over_recovery_amount),"aging_summary":s.aging_summary,"case_lines":s.case_lines,"payload_sha256":s.payload_sha256,"delivered_at":d.delivered_at,"delivery_payload_sha256":d.delivery_payload_sha256})
        return out
    def traceability(self,case_id,user_id):
        self._reader(user_id);c=self.session.scalar(select(RecoverySettlementCaseModel).where(RecoverySettlementCaseModel.tenant_id==self.tenant_id,RecoverySettlementCaseModel.settlement_case_id==case_id))
        if c is None:raise LookupError("settlement case not found")
        cert=self._certificate(case_id);correlations=self._correlations(case_id);statements=self.repo.statements(c.provider_organization_id) if c.provider_organization_id else []
        return {"settlement_case_id":case_id,"claim_id":c.claim_id,"lineage":{"release46_recovery_position":{"position_version_id":c.position_version_id,"position_payload_sha256":c.position_payload_sha256,"final_resolution_id":c.final_resolution_id},"release47_settlement":{"target_amount":str(c.target_amount),"verified_amount":str(c.verified_amount),"remaining_amount":str(c.remaining_amount),"evidence":[{"settlement_evidence_id":x.settlement_evidence_id,"status":x.status,"payload_sha256":x.evidence_payload_sha256} for x in self._evidence(case_id)],"ledger_correlations":[{"correlation_id":x.correlation_id,"journal_id":x.journal_id,"period_id":x.period_id,"payload_sha256":x.correlation_payload_sha256} for x in correlations],"completion_certificate":None if cert is None else {"certificate_id":cert.certificate_id,"status":cert.status,"accounting_period_id":cert.accounting_period_id,"payload_sha256":cert.payload_sha256}},"release48_intelligence":{"provider_balance_statement_versions":[{"statement_id":x.statement_id,"statement_version":x.statement_version,"source_watermark_sha256":x.source_watermark_sha256,"payload_sha256":x.payload_sha256} for x in statements],"source_watermark_sha256":self._watermark(c.provider_organization_id)}},"authority":{"ai_alters_balance":False,"ai_posts_journal":False,"ai_modifies_closeout_certificate":False,"automation_moves_funds":False}}
    def _documents(self,provider_id=None,case_id=None):
        docs=[]
        cases=self._cases(provider_id)
        if case_id:cases=[c for c in cases if c.settlement_case_id==case_id]
        for c in cases:
            m=self._case_metrics(c);docs.append({"citation_id":f"recovery_settlement:{c.settlement_case_id}","type":"settlement_case","text":_canon(m),"sha256":c.position_payload_sha256})
            for e in self._evidence(c.settlement_case_id):docs.append({"citation_id":f"settlement_evidence:{e.settlement_evidence_id}","type":"settlement_evidence","text":_canon({"type":e.evidence_type,"amount":str(e.amount),"status":e.status,"external_reference":e.external_reference,"bank_reference":e.bank_reference,"remittance_reference":e.remittance_reference}),"sha256":e.evidence_payload_sha256})
            for r in self._correlations(c.settlement_case_id):
                j=self.session.get(LedgerJournalModel,r.journal_id);docs.append({"citation_id":f"ledger_correlation:{r.correlation_id}","type":"ledger_correlation","text":_canon({"journal_id":r.journal_id,"amount":str(r.amount),"period_id":r.period_id,"journal_sha256":j.journal_sha256 if j else None}),"sha256":r.correlation_payload_sha256})
            cert=self._certificate(c.settlement_case_id)
            if cert:docs.append({"citation_id":f"completion_certificate:{cert.certificate_id}","type":"completion_certificate","text":_canon({"status":cert.status,"target":str(cert.target_amount),"verified":str(cert.verified_amount),"remaining":str(cert.remaining_amount),"period_id":cert.accounting_period_id}),"sha256":cert.payload_sha256})
        return docs
    def copilot(self,user_id,query,*,provider_organization_id=None,settlement_case_id=None,top_k=8):
        self._reader(user_id);docs=self._documents(provider_organization_id,settlement_case_id);qt=Counter(_tokens(query));scored=[]
        for d in docs:
            dt=Counter(_tokens(d["text"]+" "+d["type"]));overlap=sum(min(n,dt[t]) for t,n in qt.items());score=overlap/(math.sqrt(max(1,sum(qt.values())))*math.sqrt(max(1,sum(dt.values()))));scored.append((score,d))
        chosen=[d for score,d in sorted(scored,key=lambda x:-x[0]) if score>0][:top_k] or docs[:top_k]
        cites=[{"citation_id":d["citation_id"],"type":d["type"],"sha256":d["sha256"],"retrieval_score":round(next((s for s,x in scored if x is d),0.0),4)} for d in chosen]
        if settlement_case_id:
            c=next((x for x in self._cases(provider_organization_id) if x.settlement_case_id==settlement_case_id),None)
            fallback="No matching settlement case was found." if c is None else f"Settlement {settlement_case_id} has target {_money(c.target_amount)}, verified {_money(c.verified_amount)}, and remaining {_money(c.remaining_amount)} {c.currency}."
        else:
            p=self.portfolio(user_id,persist=False);fallback=f"Portfolio target recovery is {p['kpis']['target_recovery']}, verified recovery is {p['kpis']['verified_recovery']}, and remaining balance is {p['kpis']['remaining_balance']}."
        answer=fallback+" Evidence was retrieved only from governed Release 47 settlement and ledger-correlation records."
        if self.model_client is not None and chosen:
            instructions="Use only supplied recovery settlement/ledger evidence. Never alter balances, journals, payment instructions, closeout certificates, bank transactions, collections, or funds. Cite only supplied citation_id values."
            try:
                response=self.model_client.generate(model=self.copilot_model,instructions=instructions,input_text=_canon({"query":query,"evidence":chosen}),schema=RecoverySettlementCopilotSynthesis);parsed=response.parsed;allowed={d["citation_id"] for d in chosen}
                if not parsed.cited_ids or any(x not in allowed for x in parsed.cited_ids):raise ValueError("model citations are not fully grounded")
                answer=parsed.answer.strip()+(" Recommendations for authorized human review: "+"; ".join(parsed.recommendations) if parsed.recommendations else "");record_tokens(model=response.model,input_tokens=response.input_tokens,output_tokens=response.output_tokens)
            except Exception:pass
        answer += " This copilot is read-only/recommendation-only and cannot alter balances, journals, payment instructions, closeout certificates, bank transactions, collections, or fund movement."
        watermark=self._watermark(provider_organization_id);payload={"query":query,"answer":answer,"citations":cites,"watermark":watermark,"authority":"none"}
        row=self.repo.add(RecoverySettlementCopilotRunModel(run_id=f"rsic_{uuid4().hex}",tenant_id=self.tenant_id,requested_by_user_id=user_id,query_text=query,answer_text=answer,citations=cites,retrieval_strategy="settlement_ledger_hybrid_lexical_citation_retrieval_v1",source_watermark_sha256=watermark,accounting_authority="none",fund_movement_authority="none",payload_sha256=_sha(payload),created_at=_now()))
        record_recovery_settlement_intelligence(metric="copilot_run",value=1,attributes={"tenant_id":self.tenant_id,"citation_count":len(cites)})
        return {"run_id":row.run_id,"answer":answer,"citations":cites,"retrieval_strategy":row.retrieval_strategy,"source_watermark_sha256":watermark,"authority":{"accounting":"none","fund_movement":"none"},"payload_sha256":row.payload_sha256}
    def _emit(self,event_type,aggregate_id,event_id,payload):
        enqueue_realtime_event(self.session,envelope=EventEnvelope(event_id=f"rsi_{uuid4().hex}",event_type=event_type,tenant_id=self.tenant_id,claim_id=None,aggregate_type="recovery_settlement_intelligence",aggregate_id=str(aggregate_id),occurred_at=_now(),producer="medclaimiq-recovery-settlement-intelligence",payload=payload,metadata={"derived_read_only":True}),topic=EventTopic.CLAIMS.value)
    def refresh_system(self):
        p=self.portfolio(system=True,persist=True);return int(p["kpis"]["provider_count"])
