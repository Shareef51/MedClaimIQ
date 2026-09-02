from __future__ import annotations
import hashlib, json
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.domain.regulatory_supervisory_control import REGULATORY_SUPERVISORY_AUTHORITY
from app.domain.realtime import EventEnvelope, EventTopic
from app.models.regulatory_submission_transport import RegulatoryTransmissionModel
from app.models.regulatory_supervisory_control import *
from app.observability.metrics import record_regulatory_supervision
from app.realtime.events import enqueue_realtime_event
from app.repositories.regulatory_submission_transport import RegulatorySubmissionTransportRepository
from app.repositories.recovery_control_assurance import RecoveryControlAssuranceRepository
from app.repositories.regulatory_supervisory_control import RegulatorySupervisoryControlRepository
from app.repositories.tenancy import MembershipRepository
from app.services.review_workbench import ReviewConflictError


def _now(): return datetime.now(UTC)
def _canon(v): return json.dumps(v, sort_keys=True, separators=(",",":"), default=str)
def _sha(v): return hashlib.sha256((v if isinstance(v,str) else _canon(v)).encode()).hexdigest()
def _utc(v):
    if v is None:return None
    return v.replace(tzinfo=UTC) if v.tzinfo is None else v.astimezone(UTC)


class RegulatorySupervisoryControlService:
    READ_ROLES={"auditor","tenant_admin","accounting_controller"}
    PREPARER_ROLES={"auditor","tenant_admin","accounting_controller"}
    SUPERVISOR_ROLES={"auditor","tenant_admin"}
    ROOT_CAUSES={"schema_validation","data_quality","missing_required_field","transport_failure","regulator_rule_change","late_submission","incorrect_destination","unknown"}
    EFFECTIVENESS={"effective","partially_effective","ineffective","not_applicable"}
    def __init__(self,session:Session,tenant_id:str):
        self.session=session;self.tenant_id=tenant_id
        self.repo=RegulatorySupervisoryControlRepository(session,tenant_id)
        self.transport=RegulatorySubmissionTransportRepository(session,tenant_id)
        self.control=RecoveryControlAssuranceRepository(session,tenant_id)
        self.members=MembershipRepository(session,tenant_id)
    def _role(self,user_id,allowed,msg):
        m=self.members.get_by_user(user_id)
        if m is None or m.status!="active" or m.role not in allowed:raise ReviewConflictError(msg)
        return m
    def _reader(self,user_id):return self._role(user_id,self.READ_ROLES,"regulatory supervisory read role required")
    def _preparer(self,user_id):return self._role(user_id,self.PREPARER_ROLES,"authorized human regulatory supervisory preparer required")
    def _supervisor(self,user_id):return self._role(user_id,self.SUPERVISOR_ROLES,"authorized human regulatory supervisor required")

    def _sources(self,tx):
        rel=self.transport.release(tx.release_id);p=self.control.package(tx.package_id);cert=self.control.certification(tx.package_id)
        acks=self.transport.acknowledgments(tx.transmission_id);attempts=self.transport.attempts(tx.transmission_id);incidents=[x for x in self.transport.incidents() if x.transmission_id==tx.transmission_id]
        refs=[
            {"type":"package","id":p.package_id if p else tx.package_id,"sha256":p.locked_manifest_sha256 if p else None},
            {"type":"release","id":rel.release_id if rel else tx.release_id,"sha256":rel.release_sha256 if rel else None},
            {"type":"transmission","id":tx.transmission_id,"sha256":tx.envelope_sha256},
        ]
        if cert:refs.append({"type":"certification","id":cert.certification_id,"sha256":cert.certification_sha256})
        refs += [{"type":"acknowledgment","id":a.acknowledgment_id,"sha256":a.receipt_sha256} for a in acks]
        refs += [{"type":"delivery_attempt","id":a.attempt_id,"sha256":a.payload_sha256} for a in attempts]
        refs += [{"type":"transport_incident","id":i.incident_id,"sha256":_sha({"type":i.incident_type,"details":i.details,"created_at":i.created_at})} for i in incidents]
        refs=sorted(refs,key=lambda x:(x["type"],x["id"]))
        return {"release":rel,"package":p,"certification":cert,"acks":acks,"attempts":attempts,"incidents":incidents,"refs":refs,"watermark":_sha(refs)}

    def refresh_cases(self,*,transmission_id=None,actor_id="regulatory-supervision-worker",actor_type="monitoring_worker"):
        txs=[self.transport.transmission(transmission_id)] if transmission_id else self.transport.transmissions()
        created=0;updated=0
        for tx in [x for x in txs if x is not None]:
            s=self._sources(tx);acks=s["acks"];ack=acks[-1] if acks else None;existing=self.repo.case_for_transmission(tx.transmission_id)
            reason="submission_acknowledged" if tx.status=="acknowledged" else ("regulator_rejection" if tx.status=="rejected" else ("submission_sla_breach" if tx.deadline_at and _utc(tx.deadline_at)<_now() else "outstanding_submission"))
            sev="high" if reason in {"regulator_rejection","submission_sla_breach"} else "medium"
            if existing is None:
                row=self.repo.add(RegulatoryReconciliationCaseModel(case_id=f"rrc_{uuid4().hex}",tenant_id=self.tenant_id,transmission_id=tx.transmission_id,package_id=tx.package_id,destination_id=tx.destination_id,status="open",severity=sev,opened_reason=reason,acknowledgment_status=ack.acknowledgment_status if ack else None,rejection_root_cause=None,rejection_root_cause_rationale=None,amendment_effectiveness=None,amendment_effectiveness_rationale=None,source_snapshot_sha256=s["watermark"],source_refs=s["refs"],case_version=1,prepared_by_user_id=None,sla_deadline_at=tx.deadline_at,created_at=_now(),updated_at=_now()));created+=1;self._audit(row,"reconciliation_case.created",actor_type,actor_id,{"reason":reason});self._emit("regulatory_supervision.case.created",row.case_id,{"transmission_id":tx.transmission_id,"reason":reason})
            else:
                changed=existing.source_snapshot_sha256!=s["watermark"] or existing.acknowledgment_status!=(ack.acknowledgment_status if ack else None)
                if changed:
                    existing.source_snapshot_sha256=s["watermark"];existing.source_refs=s["refs"];existing.acknowledgment_status=ack.acknowledgment_status if ack else None;existing.updated_at=_now();existing.case_version+=1;updated+=1;self._audit(existing,"reconciliation_case.sources_refreshed",actor_type,actor_id,{"acknowledgment_status":existing.acknowledgment_status})
        record_regulatory_supervision(metric="cases_refreshed",value=created+updated,attributes={"tenant_id":self.tenant_id});return {"created":created,"updated":updated}

    def classify_rejection(self,case_id,user_id,*,root_cause,rationale,expected_case_version):
        self._preparer(user_id);c=self.repo.case(case_id,for_update=True)
        if c is None:raise LookupError("reconciliation case not found")
        if c.case_version!=expected_case_version:raise ReviewConflictError("stale reconciliation case version")
        tx=self.transport.transmission(c.transmission_id)
        if tx.status!="rejected":raise ReviewConflictError("rejection root cause applies only to rejected transmissions")
        if root_cause not in self.ROOT_CAUSES:raise ReviewConflictError("unsupported rejection root cause")
        c.rejection_root_cause=root_cause;c.rejection_root_cause_rationale=rationale;c.prepared_by_user_id=user_id;c.case_version+=1;c.updated_at=_now();self.session.flush();self._audit(c,"rejection.root_cause.classified","human_supervisory_preparer",user_id,{"root_cause":root_cause,"rationale":rationale});self._emit("regulatory_supervision.rejection.classified",case_id,{"root_cause":root_cause});return c

    def record_amendment_effectiveness(self,case_id,user_id,*,effectiveness,rationale,expected_case_version):
        self._preparer(user_id);c=self.repo.case(case_id,for_update=True)
        if c is None:raise LookupError("reconciliation case not found")
        if c.case_version!=expected_case_version:raise ReviewConflictError("stale reconciliation case version")
        if effectiveness not in self.EFFECTIVENESS:raise ReviewConflictError("unsupported amendment effectiveness")
        superseding=self.session.scalar(select(RegulatoryTransmissionModel).where(RegulatoryTransmissionModel.tenant_id==self.tenant_id,RegulatoryTransmissionModel.supersedes_transmission_id==c.transmission_id).order_by(RegulatoryTransmissionModel.created_at.desc()).limit(1))
        if superseding is None and effectiveness!="not_applicable":raise ReviewConflictError("no superseding amendment transmission exists")
        if effectiveness=="effective" and superseding is not None and superseding.status!="acknowledged":raise ReviewConflictError("amendment cannot be effective before cryptographic acknowledgment")
        c.amendment_effectiveness=effectiveness;c.amendment_effectiveness_rationale=rationale;c.prepared_by_user_id=user_id;c.case_version+=1;c.updated_at=_now();self.session.flush();self._audit(c,"amendment.effectiveness.recorded","human_supervisory_preparer",user_id,{"effectiveness":effectiveness,"superseding_transmission_id":superseding.transmission_id if superseding else None});self._emit("regulatory_supervision.amendment.effectiveness",case_id,{"effectiveness":effectiveness});return c

    def _controls(self,c):
        tx=self.transport.transmission(c.transmission_id);s=self._sources(tx);p=s["package"];cert=s["certification"];rel=s["release"];acks=s["acks"];attempts=s["attempts"];ack=acks[-1] if acks else None
        superseding=self.session.scalar(select(RegulatoryTransmissionModel).where(RegulatoryTransmissionModel.tenant_id==self.tenant_id,RegulatoryTransmissionModel.supersedes_transmission_id==tx.transmission_id).order_by(RegulatoryTransmissionModel.created_at.desc()).limit(1))
        accepted=bool(ack and ack.signature_verified and ack.acknowledgment_status=="accepted" and tx.status=="acknowledged")
        rejected_remediated=bool(tx.status=="rejected" and c.rejection_root_cause and superseding and superseding.status=="acknowledged" and c.amendment_effectiveness=="effective")
        tieout=bool(p and cert and rel and p.package_id==tx.package_id==rel.package_id and cert.package_id==p.package_id and cert.locked_manifest_sha256==p.locked_manifest_sha256==rel.locked_manifest_sha256)
        deadline_ok=True
        if tx.deadline_at:
            completed_at=ack.received_at if ack else None
            deadline_ok=bool(completed_at and _utc(completed_at)<=_utc(tx.deadline_at))
        controls=[
            ("certified_package",bool(p and cert and p.locked_manifest_sha256 and cert.locked_manifest_sha256==p.locked_manifest_sha256),True),
            ("human_release_bound",bool(rel and rel.release_sha256),True),
            ("transmission_completeness",bool(attempts and tx.external_submission_reference),True),
            ("package_to_regulator_tieout",tieout,True),
            ("cryptographic_acknowledgment",bool(ack and ack.signature_verified),True),
            ("accepted_or_effective_amendment",accepted or rejected_remediated,True),
            ("submission_sla_met",deadline_ok,False),
            ("rejection_root_cause_complete",tx.status!="rejected" or bool(c.rejection_root_cause),tx.status=="rejected"),
            ("amendment_effectiveness_complete",tx.status!="rejected" or rejected_remediated,tx.status=="rejected"),
        ]
        rows=[{"control_code":code,"passed":passed,"material":material} for code,passed,material in controls]
        blockers=[x for x in rows if x["material"] and not x["passed"]]
        return s,rows,blockers

    def prepare_attestation(self,case_id,user_id,*,expected_case_version):
        self._preparer(user_id);c=self.repo.case(case_id,for_update=True)
        if c is None:raise LookupError("reconciliation case not found")
        if c.case_version!=expected_case_version:raise ReviewConflictError("stale reconciliation case version")
        s,controls,blockers=self._controls(c);samples=s["refs"][:min(8,len(s["refs"]))];version=len(self.repo.attestations(case_id))+1;effectiveness=Decimal(str(round(100*sum(x["passed"] for x in controls)/max(1,len(controls)),2)))
        payload={"case_id":case_id,"version":version,"controls":controls,"blockers":blockers,"samples":samples,"watermark":s["watermark"]}
        row=self.repo.add(RegulatoryDeliveryControlAttestationModel(attestation_id=f"rdca_{uuid4().hex}",tenant_id=self.tenant_id,case_id=case_id,attestation_version=version,controls=controls,material_blockers=blockers,evidence_samples=samples,control_effectiveness_pct=effectiveness,source_watermark_sha256=s["watermark"],payload_sha256=_sha(payload),prepared_by_user_id=user_id,created_at=_now()))
        c.prepared_by_user_id=user_id;c.status="blocked" if blockers else "ready_for_certification";c.case_version+=1;c.updated_at=_now();self._sync_exceptions(c,controls);self.session.flush();self._audit(c,"delivery_control.attested","human_supervisory_preparer",user_id,{"attestation_id":row.attestation_id,"material_blockers":blockers});self._emit("regulatory_supervision.attestation.prepared",case_id,{"control_effectiveness_pct":float(effectiveness),"material_blocker_count":len(blockers)});return row

    def _sync_exceptions(self,c,controls):
        existing={(x.exception_code,x.status) for x in self.repo.exceptions(c.case_id)}
        for x in controls:
            if x["passed"] or (x["control_code"],"open") in existing:continue
            self.repo.add(RegulatoryComplianceExceptionModel(exception_id=f"rce_{uuid4().hex}",tenant_id=self.tenant_id,case_id=c.case_id,exception_code=x["control_code"],severity="high" if x["material"] else "medium",material=bool(x["material"]),status="open",details={"control_code":x["control_code"],"source_snapshot_sha256":c.source_snapshot_sha256},created_at=_now(),resolved_by_user_id=None,resolved_at=None,resolution_rationale=None))

    def resolve_exception(self,exception_id,user_id,*,rationale):
        self._preparer(user_id);e=self.session.scalar(select(RegulatoryComplianceExceptionModel).where(RegulatoryComplianceExceptionModel.tenant_id==self.tenant_id,RegulatoryComplianceExceptionModel.exception_id==exception_id))
        if e is None:raise LookupError("compliance exception not found")
        if e.status=="resolved":return e
        if e.material:raise ReviewConflictError("material control exception must be cleared by underlying deterministic control, not manually waived")
        e.status="resolved";e.resolved_by_user_id=user_id;e.resolved_at=_now();e.resolution_rationale=rationale;self.session.flush();c=self.repo.case(e.case_id);self._audit(c,"compliance_exception.resolved","human_supervisory_preparer",user_id,{"exception_id":e.exception_id,"rationale":rationale});return e

    def certify(self,case_id,attestation_id,user_id,*,conclusion,rationale,expected_case_version):
        self._supervisor(user_id);c=self.repo.case(case_id,for_update=True);att=self.repo.attestation(attestation_id)
        if c is None or att is None or att.case_id!=case_id:raise LookupError("case or attestation not found")
        if c.case_version!=expected_case_version:raise ReviewConflictError("stale reconciliation case version")
        if att.prepared_by_user_id==user_id:raise ReviewConflictError("maker and supervisory checker must be different humans")
        if att.material_blockers:raise ReviewConflictError("material regulatory reconciliation exceptions block supervisory certification")
        s,controls,blockers=self._controls(c)
        if blockers or s["watermark"]!=att.source_watermark_sha256:raise ReviewConflictError("source state changed or deterministic controls no longer pass; prepare a new attestation")
        if conclusion not in {"reconciled","reconciled_after_amendment"}:raise ReviewConflictError("unsupported supervisory conclusion")
        chain=self.repo.certifications(case_id);seq=len(chain)+1;prev=chain[-1].certification_sha256 if chain else None
        payload={"case_id":case_id,"attestation_id":attestation_id,"sequence":seq,"prepared_by":att.prepared_by_user_id,"supervisor":user_id,"conclusion":conclusion,"watermark":att.source_watermark_sha256,"previous":prev,"rationale":rationale}
        cert=self.repo.add(RegulatorySupervisoryCertificationModel(certification_id=f"rsc_{uuid4().hex}",tenant_id=self.tenant_id,case_id=case_id,attestation_id=attestation_id,certification_sequence=seq,prepared_by_user_id=att.prepared_by_user_id,supervisor_user_id=user_id,conclusion=conclusion,rationale=rationale,source_watermark_sha256=att.source_watermark_sha256,previous_certification_sha256=prev,certification_sha256=_sha(payload),certified_at=_now()))
        c.status="certified";c.case_version+=1;c.updated_at=_now();self.session.flush();self._audit(c,"supervisory_reconciliation.certified","human_regulatory_supervisor",user_id,{"certification_id":cert.certification_id,"conclusion":conclusion});self._emit("regulatory_supervision.certification.completed",case_id,{"certification_id":cert.certification_id,"conclusion":conclusion});record_regulatory_supervision(metric="certification_completed",value=1,attributes={"tenant_id":self.tenant_id,"conclusion":conclusion});return cert

    def annotate(self,case_id,user_id,*,annotation_type,body,source_refs,idempotency_key):
        self._reader(user_id);c=self.repo.case(case_id)
        if c is None:raise LookupError("reconciliation case not found")
        existing=self.session.scalar(select(RegulatorySupervisorAnnotationModel).where(RegulatorySupervisorAnnotationModel.tenant_id==self.tenant_id,RegulatorySupervisorAnnotationModel.idempotency_key==idempotency_key))
        if existing:return existing
        row=self.repo.add(RegulatorySupervisorAnnotationModel(annotation_id=f"rsa_{uuid4().hex}",tenant_id=self.tenant_id,case_id=case_id,reviewer_user_id=user_id,annotation_type=annotation_type,body=body,source_refs=source_refs,body_sha256=_sha({"body":body,"source_refs":source_refs}),idempotency_key=idempotency_key,created_at=_now()));self._audit(c,"supervisory.annotation.added","human_reviewer",user_id,{"annotation_id":row.annotation_id});return row

    def correspondence(self,case_id,user_id,*,direction,channel,subject,body,external_reference,idempotency_key):
        self._preparer(user_id);c=self.repo.case(case_id)
        if c is None:raise LookupError("reconciliation case not found")
        if direction not in {"inbound","outbound"}:raise ReviewConflictError("unsupported correspondence direction")
        existing=self.session.scalar(select(RegulatorySupervisorCorrespondenceModel).where(RegulatorySupervisorCorrespondenceModel.tenant_id==self.tenant_id,RegulatorySupervisorCorrespondenceModel.idempotency_key==idempotency_key))
        if existing:return existing
        row=self.repo.add(RegulatorySupervisorCorrespondenceModel(correspondence_id=f"rco_{uuid4().hex}",tenant_id=self.tenant_id,case_id=case_id,direction=direction,channel=channel,subject=subject,body=body,external_reference=external_reference,actor_user_id=user_id,payload_sha256=_sha({"direction":direction,"channel":channel,"subject":subject,"body":body,"external_reference":external_reference}),idempotency_key=idempotency_key,created_at=_now()));self._audit(c,"regulator.correspondence.recorded","human_supervisory_preparer",user_id,{"correspondence_id":row.correspondence_id,"direction":direction});return row

    def create_deadline(self,user_id,*,destination_id,deadline_key,due_date,description):
        self._preparer(user_id)
        if self.transport.destination(destination_id) is None:raise LookupError("regulatory destination not found")
        existing=self.session.scalar(select(RegulatoryCalendarDeadlineModel).where(RegulatoryCalendarDeadlineModel.tenant_id==self.tenant_id,RegulatoryCalendarDeadlineModel.destination_id==destination_id,RegulatoryCalendarDeadlineModel.deadline_key==deadline_key))
        if existing:return existing
        row=self.repo.add(RegulatoryCalendarDeadlineModel(deadline_id=f"rcd_{uuid4().hex}",tenant_id=self.tenant_id,destination_id=destination_id,deadline_key=deadline_key,due_date=due_date,description=description,status="open",linked_case_id=None,created_by_user_id=user_id,created_at=_now()));return row

    def dashboard(self,user_id):
        self._reader(user_id);self.refresh_cases(actor_id="dashboard-refresh",actor_type="derived_monitoring")
        cases=self.repo.cases();exceptions=self.repo.exceptions();deadlines=self.repo.deadlines();now=_now();open_cases=[x for x in cases if x.status!="certified"]
        aging=[]
        for c in cases:
            age=max(0,(now-_utc(c.created_at)).days);bucket="0-2d" if age<=2 else "3-7d" if age<=7 else "8-30d" if age<=30 else "31+d";aging.append({"case_id":c.case_id,"age_days":age,"aging_bucket":bucket,"status":c.status,"severity":c.severity})
        kpis={"cases":len(cases),"open_cases":len(open_cases),"certified":sum(x.status=="certified" for x in cases),"material_exceptions":sum(x.status=="open" and x.material for x in exceptions),"sla_breaches":sum(bool(x.sla_deadline_at and _utc(x.sla_deadline_at)<now and x.status!="certified") for x in cases),"upcoming_deadlines":sum(x.status=="open" and x.due_date>=date.today() for x in deadlines)}
        record_regulatory_supervision(metric="open_cases",value=kpis["open_cases"],attributes={"tenant_id":self.tenant_id});case_views=[]
        for x in cases:
            v=self._case_view(x);atts=self.repo.attestations(x.case_id);certs=self.repo.certifications(x.case_id);latest=atts[-1] if atts else None
            v["latest_attestation"]={"attestation_id":latest.attestation_id,"attestation_version":latest.attestation_version,"material_blockers":latest.material_blockers,"control_effectiveness_pct":float(latest.control_effectiveness_pct)} if latest else None
            v["latest_certification"]={"certification_id":certs[-1].certification_id,"conclusion":certs[-1].conclusion,"supervisor_user_id":certs[-1].supervisor_user_id} if certs else None
            case_views.append(v)
        return {"authority":REGULATORY_SUPERVISORY_AUTHORITY,"kpis":kpis,"cases":case_views,"aging":aging,"exceptions":[self._exception_view(x) for x in exceptions],"deadlines":[{"deadline_id":x.deadline_id,"destination_id":x.destination_id,"deadline_key":x.deadline_key,"due_date":x.due_date,"description":x.description,"status":x.status} for x in deadlines]}

    def traceability(self,case_id,user_id):
        self._reader(user_id);c=self.repo.case(case_id)
        if c is None:raise LookupError("reconciliation case not found")
        tx=self.transport.transmission(c.transmission_id);ttrace=None
        if tx:
            rel=self.transport.release(tx.release_id);p=self.control.package(tx.package_id);cert=self.control.certification(tx.package_id)
            ttrace={"transmission_id":tx.transmission_id,"status":tx.status,"external_submission_reference":tx.external_submission_reference,"supersedes_transmission_id":tx.supersedes_transmission_id,"release_sha256":rel.release_sha256 if rel else None,"package_id":p.package_id if p else None,"package_version":p.package_version if p else None,"locked_manifest_sha256":p.locked_manifest_sha256 if p else None,"release49_certification_sha256":cert.certification_sha256 if cert else None,"acknowledgments":[{"status":a.acknowledgment_status,"receipt_sha256":a.receipt_sha256,"signature_verified":a.signature_verified} for a in self.transport.acknowledgments(tx.transmission_id)]}
        return {"case":self._case_view(c),"release49_release50":ttrace,"attestations":[{"attestation_id":a.attestation_id,"version":a.attestation_version,"control_effectiveness_pct":float(a.control_effectiveness_pct),"material_blockers":a.material_blockers,"source_watermark_sha256":a.source_watermark_sha256,"payload_sha256":a.payload_sha256} for a in self.repo.attestations(case_id)],"certifications":[{"certification_id":x.certification_id,"sequence":x.certification_sequence,"prepared_by_user_id":x.prepared_by_user_id,"supervisor_user_id":x.supervisor_user_id,"conclusion":x.conclusion,"certification_sha256":x.certification_sha256,"previous_certification_sha256":x.previous_certification_sha256} for x in self.repo.certifications(case_id)],"exceptions":[self._exception_view(x) for x in self.repo.exceptions(case_id)],"annotations":[{"annotation_id":x.annotation_id,"type":x.annotation_type,"body_sha256":x.body_sha256,"source_refs":x.source_refs} for x in self.repo.annotations(case_id)],"correspondence":[{"correspondence_id":x.correspondence_id,"direction":x.direction,"channel":x.channel,"external_reference":x.external_reference,"payload_sha256":x.payload_sha256} for x in self.repo.correspondence(case_id)],"audit_chain":[{"sequence":x.sequence,"event_type":x.event_type,"event_sha256":x.event_sha256,"previous_event_sha256":x.previous_event_sha256} for x in self.repo.audit(case_id)],"provenance":"Release 49 certified package -> Release 50 human release -> encrypted transmission -> cryptographic acknowledgment -> amendment lineage -> Release 51 deterministic attestation -> independent human supervisory certification","authority":REGULATORY_SUPERVISORY_AUTHORITY}

    def audit_export(self,case_id,user_id):
        trace=self.traceability(case_id,user_id);manifest={"export_type":"regulatory_supervisory_reconciliation_audit","case_id":case_id,"generated_at":_now().isoformat(),"traceability":trace};return {"manifest":manifest,"manifest_sha256":_sha(manifest),"immutable_source":True,"financial_mutation_authority":False}

    def _case_view(self,c):return {"case_id":c.case_id,"transmission_id":c.transmission_id,"package_id":c.package_id,"destination_id":c.destination_id,"status":c.status,"severity":c.severity,"opened_reason":c.opened_reason,"acknowledgment_status":c.acknowledgment_status,"rejection_root_cause":c.rejection_root_cause,"amendment_effectiveness":c.amendment_effectiveness,"source_snapshot_sha256":c.source_snapshot_sha256,"case_version":c.case_version,"sla_deadline_at":c.sla_deadline_at,"updated_at":c.updated_at}
    def _exception_view(self,x):return {"exception_id":x.exception_id,"case_id":x.case_id,"exception_code":x.exception_code,"severity":x.severity,"material":x.material,"status":x.status,"details":x.details}
    def _audit(self,c,event_type,actor_type,actor_id,details):
        chain=self.repo.audit(c.case_id);seq=len(chain)+1;prev=chain[-1].event_sha256 if chain else None;payload={"case_id":c.case_id,"sequence":seq,"event_type":event_type,"actor_type":actor_type,"actor_id":actor_id,"details":details,"previous":prev};self.repo.add(RegulatorySupervisoryAuditEventModel(audit_event_id=f"rsau_{uuid4().hex}",tenant_id=self.tenant_id,case_id=c.case_id,sequence=seq,event_type=event_type,actor_type=actor_type,actor_id=actor_id,details=details,previous_event_sha256=prev,event_sha256=_sha(payload),occurred_at=_now()))
    def _emit(self,event_type,aggregate_id,payload):enqueue_realtime_event(self.session,envelope=EventEnvelope(event_id=f"rt_{uuid4().hex}",event_type=event_type,tenant_id=self.tenant_id,claim_id=None,aggregate_type="regulatory_supervisory_control",aggregate_id=str(aggregate_id),occurred_at=_now(),producer="medclaimiq-regulatory-supervision",payload=payload,metadata={"human_supervisory_certification_required":True,"automation_authority":"monitoring_and_recommendation_only","fund_movement":False}),topic=EventTopic.CLAIMS.value)
