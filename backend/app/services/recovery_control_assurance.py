from __future__ import annotations
import hashlib, json
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.domain.recovery_control_assurance import RECOVERY_CONTROL_ASSURANCE_AUTHORITY
from app.domain.realtime import EventEnvelope, EventTopic
from app.models.accounting_ledger import AccountingPeriodModel, LedgerJournalModel
from app.models.communication_delivery import CommunicationLegalHoldModel
from app.models.recovery_settlement import RecoveryCompletionCertificateModel, RecoveryLedgerCorrelationModel, RecoverySettlementCaseModel, RecoverySettlementExceptionModel
from app.models.recovery_settlement_intelligence import ProviderRecoveryBalanceStatementModel, ProviderBalanceStatementDeliveryModel, RecoveryCloseoutReportModel
from app.models.recovery_control_assurance import *
from app.realtime.events import enqueue_realtime_event
from app.observability.metrics import record_recovery_control_assurance
from app.repositories.recovery_control_assurance import RecoveryControlAssuranceRepository
from app.repositories.tenancy import MembershipRepository
from app.services.review_workbench import ReviewConflictError


def _now(): return datetime.now(UTC)
def _canon(v): return json.dumps(v,sort_keys=True,separators=(",",":"),default=str)
def _sha(v): return hashlib.sha256((v if isinstance(v,str) else _canon(v)).encode()).hexdigest()
def _money(v): return Decimal(str(v or 0)).quantize(Decimal("0.01"))


class RecoveryControlAssuranceService:
    """Governed control-assurance over immutable recovery/accounting sources.

    This service may create derived control evidence, packages, human certifications and receipt provenance.
    It does not mutate settlement balances, journals, payment instructions, closeout certificates, bank
    transactions, collections or fund movement. External submission is represented only by a human-recorded
    receipt; there is deliberately no autonomous regulatory transport call.
    """
    READ_ROLES={"finance_operator","finance_analyst","finance_approver","accounting_controller","auditor","tenant_admin"}
    MAKER_ROLES={"finance_analyst","accounting_controller","auditor","tenant_admin"}
    CHECKER_ROLES={"accounting_controller","auditor","tenant_admin"}
    SUBMISSION_ROLES={"auditor","tenant_admin"}
    def __init__(self,session:Session,tenant_id:str):
        self.session=session;self.tenant_id=tenant_id;self.repo=RecoveryControlAssuranceRepository(session,tenant_id);self.members=MembershipRepository(session,tenant_id)
    def _membership(self,user_id):
        m=self.members.get_by_user(user_id)
        if m is None or m.status!="active":raise ReviewConflictError("active tenant membership required")
        return m
    def _role(self,user_id,allowed,msg):
        m=self._membership(user_id)
        if m.role not in allowed:raise ReviewConflictError(msg)
        return m
    def _reader(self,user_id): return self._role(user_id,self.READ_ROLES,"control-assurance read role required")
    def _maker(self,user_id): return self._role(user_id,self.MAKER_ROLES,"authorized human control-assurance maker required")
    def _checker(self,user_id): return self._role(user_id,self.CHECKER_ROLES,"authorized independent human checker required")
    def _submitter(self,user_id): return self._role(user_id,self.SUBMISSION_ROLES,"authorized human regulatory/audit submitter required")

    def create_reporting_period(self,user_id,*,period_key,report_type,jurisdiction,start_date,end_date,accounting_period_ids,idempotency_key):
        self._maker(user_id)
        existing=self.repo.period_by_key(period_key)
        if existing:return existing
        if start_date>end_date:raise ReviewConflictError("reporting period start_date must not exceed end_date")
        if not accounting_period_ids:raise ReviewConflictError("at least one accounting period is required")
        periods=[]
        for pid in accounting_period_ids:
            row=self.session.scalar(select(AccountingPeriodModel).where(AccountingPeriodModel.tenant_id==self.tenant_id,AccountingPeriodModel.period_id==pid))
            if row is None:raise LookupError(f"accounting period not found: {pid}")
            periods.append(row)
        row=self.repo.add(RegulatoryReportingPeriodModel(reporting_period_id=f"rrp_{uuid4().hex}",tenant_id=self.tenant_id,period_key=period_key,report_type=report_type,jurisdiction=jurisdiction,start_date=start_date,end_date=end_date,accounting_period_ids=list(dict.fromkeys(accounting_period_ids)),status="open",period_version=1,created_by_user_id=user_id,idempotency_key=idempotency_key,created_at=_now()))
        self._audit(row.reporting_period_id,None,"reporting_period.created","human_maker",user_id,{"period_key":period_key,"accounting_period_ids":row.accounting_period_ids})
        self._emit("recovery_control_assurance.reporting_period.created",row.reporting_period_id,{"period_key":period_key})
        return row

    def _period_sources(self,period):
        certs=list(self.session.scalars(select(RecoveryCompletionCertificateModel).where(RecoveryCompletionCertificateModel.tenant_id==self.tenant_id,RecoveryCompletionCertificateModel.accounting_period_id.in_(period.accounting_period_ids))))
        cases=[];correlations=[];journals=[];exceptions=[];providers=set();claims=set()
        for cert in certs:
            case=self.session.scalar(select(RecoverySettlementCaseModel).where(RecoverySettlementCaseModel.tenant_id==self.tenant_id,RecoverySettlementCaseModel.settlement_case_id==cert.settlement_case_id))
            if case:
                cases.append(case);claims.add(case.claim_id)
                if case.provider_organization_id:providers.add(case.provider_organization_id)
                correlations += list(self.session.scalars(select(RecoveryLedgerCorrelationModel).where(RecoveryLedgerCorrelationModel.tenant_id==self.tenant_id,RecoveryLedgerCorrelationModel.settlement_case_id==case.settlement_case_id)))
                exceptions += list(self.session.scalars(select(RecoverySettlementExceptionModel).where(RecoverySettlementExceptionModel.tenant_id==self.tenant_id,RecoverySettlementExceptionModel.settlement_case_id==case.settlement_case_id,RecoverySettlementExceptionModel.status=="open")))
        for corr in correlations:
            j=self.session.scalar(select(LedgerJournalModel).where(LedgerJournalModel.tenant_id==self.tenant_id,LedgerJournalModel.journal_id==corr.journal_id))
            if j:journals.append(j)
        accounting_periods=[self.session.scalar(select(AccountingPeriodModel).where(AccountingPeriodModel.tenant_id==self.tenant_id,AccountingPeriodModel.period_id==pid)) for pid in period.accounting_period_ids]
        statements=[];deliveries=[]
        for provider in sorted(providers):
            latest=self.session.scalar(select(ProviderRecoveryBalanceStatementModel).where(ProviderRecoveryBalanceStatementModel.tenant_id==self.tenant_id,ProviderRecoveryBalanceStatementModel.provider_organization_id==provider).order_by(ProviderRecoveryBalanceStatementModel.statement_version.desc()).limit(1))
            if latest:
                statements.append(latest)
                d=self.session.scalar(select(ProviderBalanceStatementDeliveryModel).where(ProviderBalanceStatementDeliveryModel.tenant_id==self.tenant_id,ProviderBalanceStatementDeliveryModel.statement_id==latest.statement_id))
                if d:deliveries.append(d)
        reports=[]
        for pid in period.accounting_period_ids:
            r=self.session.scalar(select(RecoveryCloseoutReportModel).where(RecoveryCloseoutReportModel.tenant_id==self.tenant_id,RecoveryCloseoutReportModel.report_scope=="accounting_period",RecoveryCloseoutReportModel.scope_id==pid).order_by(RecoveryCloseoutReportModel.report_version.desc()).limit(1))
            if r:reports.append(r)
        holds=list(self.session.scalars(select(CommunicationLegalHoldModel).where(CommunicationLegalHoldModel.tenant_id==self.tenant_id,CommunicationLegalHoldModel.claim_id.in_(list(claims)) if claims else False,CommunicationLegalHoldModel.released_at.is_(None)))) if claims else []
        return {"certificates":certs,"cases":cases,"correlations":correlations,"journals":journals,"exceptions":exceptions,"providers":sorted(providers),"claims":sorted(claims),"accounting_periods":[x for x in accounting_periods if x],"statements":statements,"deliveries":deliveries,"reports":reports,"legal_holds":holds}

    def _source_refs(self,s):
        refs=[]
        refs += [{"type":"completion_certificate","id":x.certificate_id,"sha256":x.payload_sha256} for x in s["certificates"]]
        refs += [{"type":"recovery_settlement","id":x.settlement_case_id,"sha256":x.position_payload_sha256} for x in s["cases"]]
        refs += [{"type":"ledger_correlation","id":x.correlation_id,"sha256":x.correlation_payload_sha256} for x in s["correlations"]]
        refs += [{"type":"ledger_journal","id":x.journal_id,"sha256":x.journal_sha256} for x in s["journals"]]
        refs += [{"type":"provider_balance_statement","id":x.statement_id,"sha256":x.payload_sha256} for x in s["statements"]]
        refs += [{"type":"provider_statement_delivery","id":x.delivery_id,"sha256":x.delivery_payload_sha256} for x in s["deliveries"]]
        refs += [{"type":"release48_closeout_report","id":x.report_id,"sha256":x.manifest_sha256} for x in s["reports"]]
        refs += [{"type":"accounting_period","id":x.period_id,"sha256":x.close_sha256 or _sha({"period":x.period_id,"status":x.status})} for x in s["accounting_periods"]]
        refs += [{"type":"legal_hold","id":x.hold_id,"sha256":_sha({"hold_id":x.hold_id,"claim_id":x.claim_id,"reason":x.reason,"placed_at":x.placed_at})} for x in s["legal_holds"]]
        return sorted(refs,key=lambda x:(x["type"],x["id"]))

    def _controls(self,period):
        s=self._period_sources(period);controls=[]
        def add(code,passed,material,details):controls.append({"control_code":code,"passed":bool(passed),"material":bool(material),"details":details})
        open_periods=[x.period_id for x in s["accounting_periods"] if x.status!="closed"]
        add("accounting_periods_closed",not open_periods,True,{"open_period_ids":open_periods})
        uncert=[x.certificate_id for x in s["certificates"] if x.status!="certified"]
        add("human_financial_closeouts_certified",not uncert,True,{"uncertified_certificate_ids":uncert,"certificate_count":len(s["certificates"])})
        corr_by_case={}
        for x in s["correlations"]:corr_by_case[x.settlement_case_id]=corr_by_case.get(x.settlement_case_id,Decimal("0"))+_money(x.amount)
        tieout=[]
        for cert in s["certificates"]:
            correlated=_money(corr_by_case.get(cert.settlement_case_id,0));expected=_money(cert.verified_amount)
            if correlated!=expected or _money(cert.remaining_amount)!=0:tieout.append({"certificate_id":cert.certificate_id,"expected":str(expected),"correlated":str(correlated),"remaining":str(_money(cert.remaining_amount))})
        add("recovery_to_ledger_tieout",not tieout,True,{"mismatches":tieout})
        bad_journals=[x.journal_id for x in s["journals"] if x.status!="posted" or _money(x.total_debits)!=_money(x.total_credits)]
        add("ledger_journals_posted_and_balanced",not bad_journals,True,{"bad_journal_ids":bad_journals})
        add("no_open_material_settlement_exceptions",not s["exceptions"],True,{"open_exception_ids":[x.exception_id for x in s["exceptions"]]})
        statement_providers={x.provider_organization_id for x in s["statements"]};missing_statements=[x for x in s["providers"] if x not in statement_providers]
        add("provider_balance_statement_completeness",not missing_statements,True,{"missing_provider_ids":missing_statements,"provider_count":len(s["providers"])})
        delivery_statement_ids={x.statement_id for x in s["deliveries"]};undelivered=[x.statement_id for x in s["statements"] if x.statement_id not in delivery_statement_ids]
        add("provider_statement_delivery_completeness",not undelivered,True,{"undelivered_statement_ids":undelivered})
        report_periods={x.scope_id for x in s["reports"]};missing_reports=[x for x in period.accounting_period_ids if x not in report_periods]
        add("release48_closeout_report_completeness",not missing_reports,True,{"missing_accounting_period_ids":missing_reports})
        add("legal_hold_retention_manifest_captured",True,False,{"active_legal_hold_ids":[x.hold_id for x in s["legal_holds"]],"destructive_purge_automatic":False,"retention_policy":"preserve_certified_submission_evidence_and_respect_active_claim_holds"})
        refs=self._source_refs(s);watermark=_sha({"period_id":period.reporting_period_id,"period_version":period.period_version,"sources":refs,"controls":controls})
        blockers=[x for x in controls if x["material"] and not x["passed"]]
        pct=round(100*sum(1 for x in controls if x["passed"])/max(1,len(controls)),2)
        return s,controls,blockers,refs,watermark,pct

    def prepare_attestation(self,period_id,user_id=None,*,system=False):
        actor_type="deterministic_control_worker" if system else "human_requested_control_preparation"
        actor_id="system:recovery-control-assurance" if system else user_id
        if not system:self._reader(user_id)
        period=self.repo.period(period_id)
        if period is None:raise LookupError("regulatory reporting period not found")
        _,controls,blockers,refs,watermark,pct=self._controls(period)
        existing=self.repo.attestation_by_watermark(period_id,watermark)
        if existing:return existing
        payload={"period_id":period_id,"controls":controls,"blockers":blockers,"source_refs":refs,"watermark":watermark,"control_effectiveness_pct":pct,"authority":"prepare_only"}
        row=self.repo.add(PortfolioControlAttestationModel(attestation_id=f"pca_{uuid4().hex}",tenant_id=self.tenant_id,reporting_period_id=period_id,attestation_version=self.repo.next_attestation_version(period_id),control_results=controls,material_blockers=blockers,control_effectiveness_pct=f"{pct:.2f}",source_refs=refs,source_watermark_sha256=watermark,payload_sha256=_sha(payload),created_by_actor_type=actor_type,created_by_actor_id=actor_id,created_at=_now()))
        self._emit("recovery_control_assurance.attestation.prepared",period_id,{"attestation_id":row.attestation_id,"material_blocker_count":len(blockers),"control_effectiveness_pct":pct})
        record_recovery_control_assurance(metric="control_effectiveness_pct",value=pct,attributes={"tenant_id":self.tenant_id,"reporting_period_id":period_id});record_recovery_control_assurance(metric="material_blocker_count",value=len(blockers),attributes={"tenant_id":self.tenant_id,"reporting_period_id":period_id})
        return row

    def create_package(self,period_id,user_id,*,correction_of_package_id=None,amendment_reason=None,idempotency_key):
        self._maker(user_id)
        if (existing:=self.repo.package_by_idem(idempotency_key)):return existing
        period=self.repo.period(period_id)
        if period is None:raise LookupError("regulatory reporting period not found")
        if correction_of_package_id:
            prior=self.repo.package(correction_of_package_id)
            if prior is None or prior.reporting_period_id!=period_id:raise ReviewConflictError("correction package must reference the same reporting period")
            if prior.status!="submitted":raise ReviewConflictError("only a submitted package can be corrected or amended")
            if not amendment_reason or len(amendment_reason.strip())<20:raise ReviewConflictError("correction/amendment reason is required")
        att=self.prepare_attestation(period_id,user_id)
        s,controls,blockers,refs,watermark,pct=self._controls(period)
        if watermark!=att.source_watermark_sha256:att=self.prepare_attestation(period_id,user_id)
        retention={"active_legal_hold_ids":[x.hold_id for x in s["legal_holds"]],"active_legal_hold_count":len(s["legal_holds"]),"destructive_purge_automatic":False,"retention_policy":"certified submission packages and evidence are retained subject to policy and active legal holds"}
        manifest={"report_type":period.report_type,"jurisdiction":period.jurisdiction,"reporting_period":{"id":period.reporting_period_id,"key":period.period_key,"start_date":period.start_date.isoformat(),"end_date":period.end_date.isoformat(),"accounting_period_ids":period.accounting_period_ids},"control_attestation":{"attestation_id":att.attestation_id,"version":att.attestation_version,"payload_sha256":att.payload_sha256,"control_effectiveness_pct":att.control_effectiveness_pct},"portfolio":{"certificate_count":len(s["certificates"]),"provider_count":len(s["providers"]),"total_certified_recovery":str(sum((_money(x.verified_amount) for x in s["certificates"] if x.status=="certified"),Decimal("0")))},"source_refs":refs,"retention_and_legal_hold":retention,"correction_of_package_id":correction_of_package_id,"amendment_reason":amendment_reason,"authority":"human_certification_required_no_automatic_submission"}
        row=self.repo.add(RegulatorySubmissionPackageModel(package_id=f"rspkg_{uuid4().hex}",tenant_id=self.tenant_id,reporting_period_id=period_id,attestation_id=att.attestation_id,package_version=self.repo.next_package_version(period_id),correction_of_package_id=correction_of_package_id,amendment_reason=amendment_reason,manifest=manifest,validation_results=controls,material_blockers=blockers,source_watermark_sha256=watermark,manifest_sha256=_sha(manifest),locked_manifest_sha256=None,status="draft",maker_user_id=user_id,checker_user_id=None,idempotency_key=idempotency_key,created_at=_now(),locked_at=None,certified_at=None,staged_at=None,submitted_at=None))
        self._create_samples(row,refs)
        self._audit(period_id,row.package_id,"submission_package.prepared","human_maker",user_id,{"package_version":row.package_version,"material_blocker_count":len(blockers),"correction_of_package_id":correction_of_package_id})
        self._emit("recovery_control_assurance.package.prepared",period_id,{"package_id":row.package_id,"package_version":row.package_version,"material_blocker_count":len(blockers)})
        return row

    def _create_samples(self,package,refs):
        selected=sorted(refs,key=lambda x:_sha({"package":package.package_id,"source":x}))[:min(10,len(refs))]
        for idx,ref in enumerate(selected,1):
            payload={"package_id":package.package_id,"sequence":idx,"source":ref,"reason":"deterministic_hash_order_control_sample"}
            self.repo.add(ControlEvidenceSampleModel(sample_id=f"ces_{uuid4().hex}",tenant_id=self.tenant_id,package_id=package.package_id,sample_sequence=idx,source_type=ref["type"],source_id=ref["id"],source_sha256=ref["sha256"],selection_reason="deterministic hash-order control evidence sample",payload_sha256=_sha(payload),created_at=_now()))

    def lock_package(self,package_id,user_id,*,expected_source_watermark_sha256):
        self._maker(user_id);row=self.repo.package(package_id,for_update=True)
        if row is None:raise LookupError("submission package not found")
        if row.maker_user_id!=user_id:raise ReviewConflictError("only the package maker may lock this prepared version")
        if row.status=="locked":return row
        if row.status!="draft":raise ReviewConflictError("only a draft package can be locked")
        period=self.repo.period(row.reporting_period_id);_,controls,blockers,_,watermark,_=self._controls(period)
        if expected_source_watermark_sha256!=row.source_watermark_sha256 or watermark!=row.source_watermark_sha256:raise ReviewConflictError("source watermark changed; prepare a new package version")
        if blockers:raise ReviewConflictError("material control exceptions block report locking")
        row.validation_results=controls;row.material_blockers=[];row.locked_manifest_sha256=_sha({"manifest_sha256":row.manifest_sha256,"source_watermark_sha256":row.source_watermark_sha256,"package_version":row.package_version});row.status="locked";row.locked_at=_now();self.session.flush()
        self._audit(row.reporting_period_id,row.package_id,"submission_package.locked","human_maker",user_id,{"locked_manifest_sha256":row.locked_manifest_sha256})
        self._emit("recovery_control_assurance.package.locked",row.reporting_period_id,{"package_id":row.package_id,"package_version":row.package_version})
        return row

    def certify_package(self,package_id,user_id,*,rationale):
        self._checker(user_id);row=self.repo.package(package_id,for_update=True)
        if row is None:raise LookupError("submission package not found")
        existing=self.repo.certification(package_id)
        if existing:return existing
        if row.status!="locked" or not row.locked_manifest_sha256:raise ReviewConflictError("package must be hash-locked before certification")
        if row.maker_user_id==user_id:raise ReviewConflictError("maker and checker must be different humans")
        period=self.repo.period(row.reporting_period_id);_,_,blockers,_,watermark,_=self._controls(period)
        if watermark!=row.source_watermark_sha256:raise ReviewConflictError("source watermark changed after lock; create a new package version")
        if blockers:raise ReviewConflictError("material control exceptions block certification")
        chain=self.repo.certifications(row.reporting_period_id);previous=chain[-1].certification_sha256 if chain else None;seq=len(chain)+1
        payload={"period_id":row.reporting_period_id,"package_id":row.package_id,"package_version":row.package_version,"maker":row.maker_user_id,"checker":user_id,"locked_manifest_sha256":row.locked_manifest_sha256,"previous":previous,"sequence":seq,"rationale":rationale}
        cert=self.repo.add(RegulatoryCertificationModel(certification_id=f"rcert_{uuid4().hex}",tenant_id=self.tenant_id,reporting_period_id=row.reporting_period_id,package_id=row.package_id,certification_sequence=seq,maker_user_id=row.maker_user_id,checker_user_id=user_id,rationale=rationale,locked_manifest_sha256=row.locked_manifest_sha256,previous_certification_sha256=previous,certification_sha256=_sha(payload),certified_at=_now()))
        row.checker_user_id=user_id;row.status="certified";row.certified_at=cert.certified_at;self.session.flush()
        self._audit(row.reporting_period_id,row.package_id,"submission_package.certified","human_checker",user_id,{"certification_id":cert.certification_id,"certification_sha256":cert.certification_sha256})
        self._emit("recovery_control_assurance.package.certified",row.reporting_period_id,{"package_id":row.package_id,"certification_id":cert.certification_id})
        record_recovery_control_assurance(metric="human_certified_package",value=1,attributes={"tenant_id":self.tenant_id,"reporting_period_id":row.reporting_period_id})
        return cert

    def stage_submission(self,package_id,user_id,*,rationale):
        self._submitter(user_id);row=self.repo.package(package_id,for_update=True)
        if row is None:raise LookupError("submission package not found")
        if row.status=="staged":return row
        if row.status!="certified" or self.repo.certification(package_id) is None:raise ReviewConflictError("human maker-checker certification required before submission staging")
        row.status="staged";row.staged_at=_now();self.session.flush();self._audit(row.reporting_period_id,row.package_id,"submission.staged","human_regulatory_submitter",user_id,{"rationale":rationale,"automatic_submission":False});self._emit("recovery_control_assurance.submission.staged",row.reporting_period_id,{"package_id":row.package_id});return row

    def record_submission_receipt(self,package_id,user_id,*,external_submission_id,submission_status,external_receipt_reference,receipt_metadata,idempotency_key):
        self._submitter(user_id);row=self.repo.package(package_id,for_update=True)
        if row is None:raise LookupError("submission package not found")
        if (existing:=self.repo.receipt(package_id)):return existing
        if row.status!="staged":raise ReviewConflictError("package must be human-staged before recording an external submission receipt")
        payload={"package_id":package_id,"locked_manifest_sha256":row.locked_manifest_sha256,"external_submission_id":external_submission_id,"submission_status":submission_status,"external_receipt_reference":external_receipt_reference,"receipt_metadata":receipt_metadata,"submitted_by_user_id":user_id}
        receipt=self.repo.add(RegulatorySubmissionReceiptModel(receipt_id=f"rsr_{uuid4().hex}",tenant_id=self.tenant_id,package_id=package_id,external_submission_id=external_submission_id,submission_status=submission_status,external_receipt_reference=external_receipt_reference,receipt_metadata=receipt_metadata,submitted_by_user_id=user_id,payload_sha256=_sha(payload),idempotency_key=idempotency_key,received_at=_now()))
        row.status="submitted";row.submitted_at=receipt.received_at;self.session.flush();self._audit(row.reporting_period_id,row.package_id,"submission.receipt_recorded","human_regulatory_submitter",user_id,{"receipt_id":receipt.receipt_id,"submission_status":submission_status,"external_submission_id":external_submission_id});self._emit("recovery_control_assurance.submission.receipt_recorded",row.reporting_period_id,{"package_id":package_id,"submission_status":submission_status});return receipt

    def add_annotation(self,package_id,user_id,*,annotation_type,body,source_refs,idempotency_key):
        self._reader(user_id);package=self.repo.package(package_id)
        if package is None:raise LookupError("submission package not found")
        payload={"package_id":package_id,"reviewer_user_id":user_id,"annotation_type":annotation_type,"body":body,"source_refs":source_refs}
        row=self.repo.add(RegulatoryAuditAnnotationModel(annotation_id=f"raa_{uuid4().hex}",tenant_id=self.tenant_id,package_id=package_id,reviewer_user_id=user_id,annotation_type=annotation_type,body=body,source_refs=source_refs,body_sha256=_sha(payload),idempotency_key=idempotency_key,created_at=_now()))
        self._audit(package.reporting_period_id,package_id,"audit.annotation.added","human_audit_reviewer",user_id,{"annotation_id":row.annotation_id,"annotation_type":annotation_type});return row

    def dashboard(self,user_id):
        self._reader(user_id);periods=self.repo.periods();packages=self.repo.packages();certified=sum(1 for x in packages if x.status in {"certified","staged","submitted"});submitted=sum(1 for x in packages if x.status=="submitted")
        latest=[]
        for p in periods:
            atts=self.repo.attestations(p.reporting_period_id);att=atts[0] if atts else None;pp=self.repo.packages(p.reporting_period_id)
            latest.append({"reporting_period_id":p.reporting_period_id,"period_key":p.period_key,"status":p.status,"latest_package_status":pp[0].status if pp else "not_prepared","material_blockers":att.material_blockers if att else [],"control_effectiveness_pct":att.control_effectiveness_pct if att else None})
        effects=[float(x.control_effectiveness_pct) for p in periods for x in self.repo.attestations(p.reporting_period_id)[:1]]
        return {"authority":RECOVERY_CONTROL_ASSURANCE_AUTHORITY,"kpis":{"reporting_periods":len(periods),"packages":len(packages),"certified_packages":certified,"submitted_packages":submitted,"average_control_effectiveness_pct":round(sum(effects)/len(effects),2) if effects else 0.0,"material_blocked_periods":sum(bool(x["material_blockers"]) for x in latest)},"operational_queue":latest}

    def workbench(self,period_id,user_id):
        self._reader(user_id);period=self.repo.period(period_id)
        if period is None:raise LookupError("regulatory reporting period not found")
        att=self.repo.attestations(period_id);packages=self.repo.packages(period_id)
        return {"authority":RECOVERY_CONTROL_ASSURANCE_AUTHORITY,"period":{"reporting_period_id":period.reporting_period_id,"period_key":period.period_key,"report_type":period.report_type,"jurisdiction":period.jurisdiction,"start_date":period.start_date,"end_date":period.end_date,"accounting_period_ids":period.accounting_period_ids,"status":period.status},"latest_attestation":None if not att else self._attestation_view(att[0]),"packages":[self._package_view(x) for x in packages],"certification_chain":[{"certification_id":x.certification_id,"package_id":x.package_id,"sequence":x.certification_sequence,"maker_user_id":x.maker_user_id,"checker_user_id":x.checker_user_id,"previous_certification_sha256":x.previous_certification_sha256,"certification_sha256":x.certification_sha256,"certified_at":x.certified_at} for x in self.repo.certifications(period_id)],"audit_chain":[{"sequence":x.sequence,"event_type":x.event_type,"actor_type":x.actor_type,"actor_id":x.actor_id,"event_sha256":x.event_sha256,"previous_event_sha256":x.previous_event_sha256,"occurred_at":x.occurred_at} for x in self.repo.audit(period_id)]}

    def traceability(self,package_id,user_id):
        self._reader(user_id);p=self.repo.package(package_id)
        if p is None:raise LookupError("submission package not found")
        cert=self.repo.certification(package_id);receipt=self.repo.receipt(package_id);samples=self.repo.samples(package_id)
        return {"package":self._package_view(p),"control_evidence_samples":[{"sample_id":x.sample_id,"source_type":x.source_type,"source_id":x.source_id,"source_sha256":x.source_sha256,"payload_sha256":x.payload_sha256} for x in samples],"certification":None if cert is None else {"certification_id":cert.certification_id,"certification_sha256":cert.certification_sha256,"previous_certification_sha256":cert.previous_certification_sha256,"maker_user_id":cert.maker_user_id,"checker_user_id":cert.checker_user_id},"submission_receipt":None if receipt is None else {"receipt_id":receipt.receipt_id,"external_submission_id":receipt.external_submission_id,"submission_status":receipt.submission_status,"payload_sha256":receipt.payload_sha256},"annotations":[{"annotation_id":x.annotation_id,"reviewer_user_id":x.reviewer_user_id,"annotation_type":x.annotation_type,"body_sha256":x.body_sha256,"source_refs":x.source_refs} for x in self.repo.annotations(package_id)],"provenance":"recovery decision -> settlement evidence -> ledger reconciliation -> human financial certification -> provider statement/closeout report -> control attestation -> maker-checker certification -> human-staged external submission -> receipt","authority":{"ai_certifies":False,"automation_submits":False,"financial_records_mutated":False,"fund_movement":False}}

    def _attestation_view(self,a):return {"attestation_id":a.attestation_id,"attestation_version":a.attestation_version,"control_results":a.control_results,"material_blockers":a.material_blockers,"control_effectiveness_pct":a.control_effectiveness_pct,"source_watermark_sha256":a.source_watermark_sha256,"payload_sha256":a.payload_sha256,"created_by_actor_type":a.created_by_actor_type,"created_at":a.created_at}
    def _package_view(self,p):return {"package_id":p.package_id,"package_version":p.package_version,"status":p.status,"correction_of_package_id":p.correction_of_package_id,"amendment_reason":p.amendment_reason,"manifest":p.manifest,"validation_results":p.validation_results,"material_blockers":p.material_blockers,"source_watermark_sha256":p.source_watermark_sha256,"manifest_sha256":p.manifest_sha256,"locked_manifest_sha256":p.locked_manifest_sha256,"maker_user_id":p.maker_user_id,"checker_user_id":p.checker_user_id,"created_at":p.created_at,"locked_at":p.locked_at,"certified_at":p.certified_at,"staged_at":p.staged_at,"submitted_at":p.submitted_at}

    def _audit(self,period_id,package_id,event_type,actor_type,actor_id,details):
        chain=self.repo.audit(period_id);seq=len(chain)+1;prev=chain[-1].event_sha256 if chain else None;payload={"period_id":period_id,"package_id":package_id,"sequence":seq,"event_type":event_type,"actor_type":actor_type,"actor_id":actor_id,"details":details,"previous":prev}
        return self.repo.add(RegulatoryControlAuditEventModel(audit_event_id=f"rcae_{uuid4().hex}",tenant_id=self.tenant_id,reporting_period_id=period_id,package_id=package_id,sequence=seq,event_type=event_type,actor_type=actor_type,actor_id=actor_id,details=details,previous_event_sha256=prev,event_sha256=_sha(payload),occurred_at=_now()))
    def _emit(self,event_type,aggregate_id,payload):
        enqueue_realtime_event(self.session,envelope=EventEnvelope(event_id=f"rca_{uuid4().hex}",event_type=event_type,tenant_id=self.tenant_id,claim_id=None,aggregate_type="recovery_control_assurance",aggregate_id=str(aggregate_id),occurred_at=_now(),producer="medclaimiq-recovery-control-assurance",payload=payload,metadata={"financial_source_read_only":True,"automatic_submission":False}),topic=EventTopic.CLAIMS.value)
    def refresh_system(self):
        count=0
        for p in self.repo.periods():self.prepare_attestation(p.reporting_period_id,system=True);count+=1
        return count
