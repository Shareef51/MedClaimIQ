from __future__ import annotations
import hashlib,json,re
from collections import defaultdict
from datetime import UTC,datetime
from uuid import uuid4
from sqlalchemy.orm import Session
from app.domain.realtime import EventEnvelope,EventTopic
from app.domain.regulatory_portfolio_oversight import REGULATORY_PORTFOLIO_AUTHORITY
from app.models.regulatory_portfolio_oversight import *
from app.observability.metrics import record_regulatory_portfolio_oversight
from app.realtime.events import enqueue_realtime_event
from app.repositories.regulatory_portfolio_oversight import RegulatoryPortfolioOversightRepository
from app.repositories.regulatory_remediation import RegulatoryRemediationRepository
from app.repositories.tenancy import MembershipRepository
from app.services.review_workbench import ReviewConflictError

def _now():return datetime.now(UTC)
def _canon(v):return json.dumps(v,sort_keys=True,separators=(",",":"),default=str)
def _sha(v):return hashlib.sha256((v if isinstance(v,str) else _canon(v)).encode()).hexdigest()
def _utc(v):return v.replace(tzinfo=UTC) if v and v.tzinfo is None else v.astimezone(UTC) if v else None
def _norm(v):return re.sub(r"[^a-z0-9]+"," ",v.lower()).strip()

class RegulatoryPortfolioOversightService:
    READ_ROLES={"auditor","tenant_admin","accounting_controller"};PREP_ROLES=READ_ROLES;TEST_ROLES=READ_ROLES;MANAGEMENT_ROLES={"tenant_admin"};CERT_ROLES={"auditor","tenant_admin"}
    def __init__(self,session:Session,tenant_id:str):
        self.session=session;self.tenant_id=tenant_id;self.repo=RegulatoryPortfolioOversightRepository(session,tenant_id);self.rem=RegulatoryRemediationRepository(session,tenant_id);self.members=MembershipRepository(session,tenant_id)
    def _role(self,user_id,allowed,msg):
        m=self.members.get_by_user(user_id)
        if m is None or m.status!="active" or m.role not in allowed:raise ReviewConflictError(msg)
        return m
    def _reader(self,u):return self._role(u,self.READ_ROLES,"regulatory portfolio oversight read role required")
    def _preparer(self,u):return self._role(u,self.PREP_ROLES,"authorized human portfolio-control preparer required")
    def _tester(self,u):return self._role(u,self.TEST_ROLES,"authorized independent human control tester required")
    def _manager(self,u):return self._role(u,self.MANAGEMENT_ROLES,"authorized human management attester required")
    def _certifier(self,u):return self._role(u,self.CERT_ROLES,"authorized independent human portfolio certifier required")
    def _snapshot(self,sid):
        s=self.repo.snapshot(sid)
        if s is None:raise LookupError("regulatory portfolio snapshot not found")
        return s
    def register_control(self,user_id,*,control_key,name,description,control_family,owner_user_id):
        self._preparer(user_id);self._preparer(owner_user_id);existing=[x for x in self.repo.controls() if x.control_key==control_key];version=len(existing)+1
        row=self.repo.add(EnterpriseControlModel(control_id=f"ectl_{uuid4().hex}",tenant_id=self.tenant_id,control_key=control_key,control_version=version,name=name,description=description,control_family=control_family,owner_user_id=owner_user_id,status="active",created_by_user_id=user_id,created_at=_now()))
        return row
    def map_control(self,control_id,user_id,*,plan_id,mapping_rationale):
        self._preparer(user_id);c=self.repo.control(control_id);p=self.rem.plan(plan_id)
        if c is None:raise LookupError("enterprise control not found")
        if p is None:raise LookupError("regulatory remediation plan not found")
        prior=next((x for x in self.repo.mappings_for_plan(plan_id) if x.control_id==control_id),None)
        if prior:return prior
        return self.repo.add(RegulatoryControlFindingMapModel(mapping_id=f"rcfm_{uuid4().hex}",tenant_id=self.tenant_id,control_id=control_id,plan_id=plan_id,mapping_rationale=mapping_rationale,mapped_by_user_id=user_id,mapped_at=_now()))
    def prepare_snapshot(self,user_id,*,period_key):
        self._preparer(user_id);plans=self.rem.plans();mappings=self.repo.mappings();now=_now();roots=defaultdict(list);codes=defaultdict(list);control_groups=defaultdict(list);all_tasks=[];closed_effective=0
        for p in plans:
            roots[_norm(p.root_cause)].append(p);codes[p.finding_code].append(p);all_tasks.extend(self.rem.tasks(p.plan_id));closed_effective+=int(p.status=="closed" and any(c.conclusion=="effective" for c in self.rem.certifications(p.plan_id)))
        for m in mappings:control_groups[m.control_id].append(self.rem.plan(m.plan_id))
        groups=[]
        for typ,d in (("recurring_root_cause",roots),("repeat_finding",codes),("systemic_control",control_groups)):
            for key,members in d.items():
                members=[x for x in members if x is not None]
                if len(members)>=2:groups.append((typ,key,members))
        avg=round(sum(p.risk_score for p in plans)/len(plans)) if plans else 0;overdue=[t for t in all_tasks if t.status!="completed" and _utc(t.due_at)<now];critical_path=sorted([{"plan_id":t.plan_id,"task_key":t.task_key,"due_at":_utc(t.due_at).isoformat(),"dependency_count":len(t.dependency_keys)} for t in all_tasks if t.status!="completed"],key=lambda x:(x["due_at"],-x["dependency_count"]))[:20]
        risk=min(100,avg+min(20,len(groups)*5)+min(15,len(overdue)*3));effect=round(100*closed_effective/len(plans)) if plans else 100
        source={"plans":[{"id":p.plan_id,"sha":p.plan_sha256,"status":p.status,"risk":p.risk_score} for p in sorted(plans,key=lambda x:x.plan_id)],"tasks":[{"id":t.task_id,"status":t.status,"due":_utc(t.due_at).isoformat()} for t in sorted(all_tasks,key=lambda x:x.task_id)],"mappings":[{"control":m.control_id,"plan":m.plan_id} for m in sorted(mappings,key=lambda x:x.mapping_id)]}
        version=len(self.repo.snapshots_for_period(period_key))+1
        row=self.repo.add(RegulatoryPortfolioSnapshotModel(snapshot_id=f"rpos_{uuid4().hex}",tenant_id=self.tenant_id,period_key=period_key,snapshot_version=version,status="prepared",plan_count=len(plans),open_plan_count=sum(p.status!="closed" for p in plans),overdue_task_count=len(overdue),repeat_finding_count=sum(1 for _,m in codes.items() if len(m)>=2),recurring_root_cause_count=sum(1 for _,m in roots.items() if len(m)>=2),systemic_cluster_count=len(groups),average_risk_score=avg,portfolio_risk_score=risk,control_effectiveness_pct=effect,critical_path=critical_path,portfolio_metrics={"closed_effective":closed_effective,"mapped_controls":len({m.control_id for m in mappings}),"repeat_findings":sum(1 for m in codes.values() if len(m)>=2),"recurring_root_causes":sum(1 for m in roots.values() if len(m)>=2)},source_watermark_sha256=_sha(source),prepared_by_user_id=user_id,created_at=_now()))
        for typ,key,members in groups:
            maxrisk=max(p.risk_score for p in members);sev="critical" if maxrisk>=85 or len(members)>=4 else "high" if maxrisk>=65 else "medium";payload={"type":typ,"key":key,"plans":[p.plan_id for p in members],"severity":sev}
            self.repo.add(RegulatorySystemicRiskClusterModel(cluster_id=f"rpsc_{uuid4().hex}",tenant_id=self.tenant_id,snapshot_id=row.snapshot_id,cluster_key=f"{typ}:{key}",cluster_type=typ,severity=sev,member_plan_ids=[p.plan_id for p in members],member_count=len(members),recommendation={"authority":"none","recommendation_only":True,"action":"Perform cross-finding human control review, validate recurrence drivers, and independently test the mapped enterprise control."},payload_sha256=_sha(payload),created_at=_now()))
        self._audit(row,"snapshot.prepared","human_portfolio_preparer",user_id,{"plan_count":len(plans),"systemic_clusters":len(groups),"authority":"analysis_only"});self._emit("regulatory_portfolio.snapshot.prepared",row.snapshot_id,{"period_key":period_key,"risk_score":risk});record_regulatory_portfolio_oversight(metric="portfolio_risk_score",value=risk,attributes={"tenant_id":self.tenant_id,"period_key":period_key});return row
    def create_testing_campaign(self,snapshot_id,user_id,*,campaign_key,methodology,control_ids,due_at):
        self._preparer(user_id);self._snapshot(snapshot_id)
        if not control_ids:raise ReviewConflictError("testing campaign requires at least one enterprise control")
        if any(self.repo.control(c) is None for c in control_ids):raise ReviewConflictError("testing campaign contains unknown enterprise control")
        due=_utc(due_at)
        if due<=_now():raise ReviewConflictError("testing campaign due date must be in the future")
        row=self.repo.add(RegulatoryControlTestingCampaignModel(campaign_id=f"rptc_{uuid4().hex}",tenant_id=self.tenant_id,snapshot_id=snapshot_id,campaign_key=campaign_key,status="open",methodology=methodology,control_ids=control_ids,prepared_by_user_id=user_id,due_at=due,created_at=_now(),completed_at=None));self._audit(self._snapshot(snapshot_id),"testing_campaign.created","human_portfolio_preparer",user_id,{"campaign_id":row.campaign_id,"controls":control_ids});return row
    def record_test_result(self,campaign_id,user_id,*,control_id,outcome,observations,evidence_refs):
        self._tester(user_id);c=self.repo.campaign(campaign_id)
        if c is None:raise LookupError("control testing campaign not found")
        if user_id==c.prepared_by_user_id:raise ReviewConflictError("control testing campaign preparer and independent tester must be different humans")
        if control_id not in c.control_ids:raise ReviewConflictError("control is not in this testing campaign")
        if outcome not in {"pass","fail","partial"}:raise ReviewConflictError("unsupported independent control test outcome")
        if not evidence_refs:raise ReviewConflictError("independent control test evidence is required")
        prior=next((x for x in self.repo.results(campaign_id) if x.control_id==control_id),None)
        if prior:return prior
        payload={"campaign":campaign_id,"control":control_id,"outcome":outcome,"observations":observations,"evidence":evidence_refs,"tester":user_id}
        row=self.repo.add(RegulatoryControlTestingResultModel(result_id=f"rptr_{uuid4().hex}",tenant_id=self.tenant_id,campaign_id=campaign_id,control_id=control_id,outcome=outcome,observations=observations,evidence_refs=evidence_refs,tested_by_user_id=user_id,payload_sha256=_sha(payload),tested_at=_now()))
        if {x.control_id for x in self.repo.results(campaign_id)}==set(c.control_ids):c.status="completed";c.completed_at=_now();self.session.flush()
        self._audit(self._snapshot(c.snapshot_id),"control_test.recorded","human_independent_tester",user_id,{"campaign_id":campaign_id,"control_id":control_id,"outcome":outcome});return row
    def request_risk_acceptance(self,snapshot_id,user_id,*,risk_key,rationale,expires_at):
        self._preparer(user_id);self._snapshot(snapshot_id);exp=_utc(expires_at)
        if exp<=_now():raise ReviewConflictError("risk acceptance expiry must be in the future")
        prior=self.repo.risk_acceptance(snapshot_id,risk_key)
        if prior:return prior
        row=self.repo.add(RegulatoryRiskAcceptanceModel(acceptance_id=f"rpra_{uuid4().hex}",tenant_id=self.tenant_id,snapshot_id=snapshot_id,risk_key=risk_key,status="pending",rationale=rationale,requested_by_user_id=user_id,decided_by_user_id=None,decision_rationale=None,expires_at=exp,created_at=_now(),decided_at=None));self._audit(self._snapshot(snapshot_id),"risk_acceptance.requested","human_risk_requester",user_id,{"risk_key":risk_key});return row
    def decide_risk_acceptance(self,snapshot_id,risk_key,user_id,*,approve,decision_rationale):
        self._certifier(user_id);a=self.repo.risk_acceptance(snapshot_id,risk_key)
        if a is None:raise LookupError("portfolio risk acceptance not found")
        if user_id==a.requested_by_user_id:raise ReviewConflictError("risk requester and approver must be different humans")
        if a.status!="pending":raise ReviewConflictError("risk acceptance already decided")
        a.status="approved" if approve else "rejected";a.decided_by_user_id=user_id;a.decision_rationale=decision_rationale;a.decided_at=_now();self.session.flush();self._audit(self._snapshot(snapshot_id),"risk_acceptance.decided","human_risk_approver",user_id,{"risk_key":risk_key,"status":a.status});return a
    def management_attest(self,snapshot_id,user_id,*,conclusion,rationale):
        self._manager(user_id);s=self._snapshot(snapshot_id)
        if user_id==s.prepared_by_user_id:raise ReviewConflictError("snapshot preparer and management attester must be different humans")
        if conclusion not in {"effective","needs_action"}:raise ReviewConflictError("unsupported management attestation conclusion")
        prior=self.repo.management_attestation(snapshot_id)
        if prior:return prior
        payload={"snapshot":snapshot_id,"conclusion":conclusion,"rationale":rationale,"source":s.source_watermark_sha256,"attester":user_id}
        row=self.repo.add(RegulatoryManagementAttestationModel(attestation_id=f"rpma_{uuid4().hex}",tenant_id=self.tenant_id,snapshot_id=snapshot_id,conclusion=conclusion,rationale=rationale,attested_by_user_id=user_id,source_watermark_sha256=s.source_watermark_sha256,attestation_sha256=_sha(payload),attested_at=_now()));self._audit(s,"management.attested","human_management_attester",user_id,{"conclusion":conclusion});return row
    def certify_portfolio(self,snapshot_id,user_id,*,conclusion,rationale):
        self._certifier(user_id);s=self._snapshot(snapshot_id);att=self.repo.management_attestation(snapshot_id)
        if att is None or att.conclusion!="effective":raise ReviewConflictError("effective human management attestation required before portfolio certification")
        if user_id in {s.prepared_by_user_id,att.attested_by_user_id}:raise ReviewConflictError("portfolio preparer/management attester and independent certifier must be different humans")
        campaigns=self.repo.campaigns(snapshot_id)
        if not campaigns or any(c.status!="completed" for c in campaigns):raise ReviewConflictError("completed independent control testing campaign required before portfolio certification")
        results=[r for c in campaigns for r in self.repo.results(c.campaign_id)]
        if any(r.outcome!="pass" for r in results):raise ReviewConflictError("failed or partial control testing blocks portfolio certification")
        approved={a.risk_key for a in self.repo.risk_acceptances(snapshot_id) if a.status=="approved" and _utc(a.expires_at)>_now()}
        critical=[c.cluster_key for c in self.repo.clusters(snapshot_id) if c.severity=="critical" and c.cluster_key not in approved]
        if critical:raise ReviewConflictError("unaccepted critical systemic risk blocks portfolio certification")
        chain=self.repo.certifications(snapshot_id);seq=len(chain)+1;prev=chain[-1].certification_sha256 if chain else None;payload={"snapshot":snapshot_id,"sequence":seq,"conclusion":conclusion,"source":s.source_watermark_sha256,"attestation":att.attestation_sha256,"previous":prev,"certifier":user_id}
        row=self.repo.add(RegulatoryPortfolioCertificationModel(certification_id=f"rpcert_{uuid4().hex}",tenant_id=self.tenant_id,snapshot_id=snapshot_id,certification_sequence=seq,conclusion=conclusion,rationale=rationale,certified_by_user_id=user_id,source_watermark_sha256=s.source_watermark_sha256,previous_certification_sha256=prev,certification_sha256=_sha(payload),certified_at=_now()));s.status="certified";self.session.flush();self._audit(s,"portfolio.certified","human_independent_portfolio_certifier",user_id,{"certification_id":row.certification_id,"conclusion":conclusion});self._emit("regulatory_portfolio.certified",snapshot_id,{"certification_id":row.certification_id});return row
    def dashboard(self,user_id):
        self._reader(user_id);snaps=self.repo.snapshots();latest=snaps[0] if snaps else None
        return {"snapshot_count":len(snaps),"latest":self.snapshot_view(latest.snapshot_id,user_id) if latest else None,"authority":REGULATORY_PORTFOLIO_AUTHORITY}
    def monitor_portfolio(self,actor_id="regulatory-portfolio-worker",actor_type="monitoring_worker"):
        snaps=self.repo.snapshots();open_count=sum(s.status!="certified" for s in snaps);critical=sum(len([c for c in self.repo.clusters(s.snapshot_id) if c.severity=="critical"]) for s in snaps);record_regulatory_portfolio_oversight(metric="open_portfolio_snapshots",value=open_count,attributes={"tenant_id":self.tenant_id,"actor_type":actor_type});return open_count+critical
    def snapshot_view(self,snapshot_id,user_id):
        self._reader(user_id);s=self._snapshot(snapshot_id);clusters=self.repo.clusters(snapshot_id);campaigns=self.repo.campaigns(snapshot_id);att=self.repo.management_attestation(snapshot_id);certs=self.repo.certifications(snapshot_id)
        return {"snapshot_id":s.snapshot_id,"period_key":s.period_key,"snapshot_version":s.snapshot_version,"status":s.status,"metrics":{"plan_count":s.plan_count,"open_plan_count":s.open_plan_count,"overdue_task_count":s.overdue_task_count,"repeat_finding_count":s.repeat_finding_count,"recurring_root_cause_count":s.recurring_root_cause_count,"systemic_cluster_count":s.systemic_cluster_count,"average_risk_score":s.average_risk_score,"portfolio_risk_score":s.portfolio_risk_score,"control_effectiveness_pct":s.control_effectiveness_pct},"critical_path":s.critical_path,"source_watermark_sha256":s.source_watermark_sha256,"clusters":[{"cluster_key":c.cluster_key,"type":c.cluster_type,"severity":c.severity,"member_count":c.member_count,"member_plan_ids":c.member_plan_ids,"recommendation":c.recommendation,"payload_sha256":c.payload_sha256} for c in clusters],"controls":[{"control_id":c.control_id,"control_key":c.control_key,"name":c.name,"family":c.control_family,"version":c.control_version} for c in self.repo.controls()],"campaigns":[{"campaign_id":c.campaign_id,"campaign_key":c.campaign_key,"status":c.status,"control_ids":c.control_ids,"results":[{"control_id":r.control_id,"outcome":r.outcome,"tester":r.tested_by_user_id,"payload_sha256":r.payload_sha256} for r in self.repo.results(c.campaign_id)]} for c in campaigns],"risk_acceptances":[{"risk_key":a.risk_key,"status":a.status,"expires_at":a.expires_at} for a in self.repo.risk_acceptances(snapshot_id)],"management_attestation":{"conclusion":att.conclusion,"attested_by":att.attested_by_user_id,"attestation_sha256":att.attestation_sha256} if att else None,"certifications":[{"sequence":c.certification_sequence,"conclusion":c.conclusion,"certified_by":c.certified_by_user_id,"certification_sha256":c.certification_sha256,"previous_certification_sha256":c.previous_certification_sha256} for c in certs],"authority":REGULATORY_PORTFOLIO_AUTHORITY}
    def board_regulatory_package(self,snapshot_id,user_id):
        view=self.snapshot_view(snapshot_id,user_id);manifest={"package_type":"regulatory_remediation_portfolio_assurance","generated_at":_now().isoformat(),"snapshot":view,"read_only_source":True,"ai_authority":"analysis_recommendation_only","financial_accounting_mutation_authority":False,"fund_movement":False};return {"manifest":manifest,"manifest_sha256":_sha(manifest),"immutable_source":True}
    def _audit(self,s,event_type,actor_type,actor_id,details):
        chain=self.repo.audit(s.snapshot_id);seq=len(chain)+1;prev=chain[-1].event_sha256 if chain else None;payload={"snapshot":s.snapshot_id,"sequence":seq,"event_type":event_type,"actor_type":actor_type,"actor_id":actor_id,"details":details,"previous":prev};self.repo.add(RegulatoryPortfolioAuditEventModel(audit_event_id=f"rpau_{uuid4().hex}",tenant_id=self.tenant_id,snapshot_id=s.snapshot_id,sequence=seq,event_type=event_type,actor_type=actor_type,actor_id=actor_id,details=details,previous_event_sha256=prev,event_sha256=_sha(payload),occurred_at=_now()))
    def _emit(self,event_type,aggregate_id,payload):enqueue_realtime_event(self.session,envelope=EventEnvelope(event_id=f"rt_{uuid4().hex}",event_type=event_type,tenant_id=self.tenant_id,claim_id=None,aggregate_type="regulatory_portfolio",aggregate_id=str(aggregate_id),occurred_at=_now(),producer="medclaimiq-regulatory-portfolio-oversight",payload=payload,metadata={"ai_authority":"analysis_recommendation_only","human_certification_required":True,"financial_accounting_mutation_authority":False,"fund_movement":False}),topic=EventTopic.CLAIMS.value)
