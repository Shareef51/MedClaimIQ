from __future__ import annotations
import hashlib,json
from datetime import UTC,datetime,timedelta
from uuid import uuid4
from sqlalchemy.orm import Session
from app.domain.regulatory_assurance_deficiencies import REGULATORY_ASSURANCE_DEFICIENCY_AUTHORITY
from app.models.regulatory_assurance_deficiencies import *
from app.repositories.regulatory_assurance_deficiencies import RegulatoryAssuranceDeficiencyRepository
from app.repositories.tenancy import MembershipRepository
from app.services.review_workbench import ReviewConflictError

def _now():return datetime.now(UTC)
def _sha(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()
def _severity(score):return "critical" if score>=90 else "high" if score>=70 else "moderate" if score>=40 else "low"

class RegulatoryAssuranceDeficiencyService:
    READ={"auditor","tenant_admin","accounting_controller"}; PREP=READ; ESCALATE={"auditor"}; CLOSE={"auditor"}
    def __init__(self,session:Session,tenant_id:str):self.session=session;self.tenant_id=tenant_id;self.repo=RegulatoryAssuranceDeficiencyRepository(session,tenant_id);self.members=MembershipRepository(session,tenant_id)
    def _role(self,user_id,allowed,msg):
        m=self.members.get_by_user(user_id)
        if m is None or m.status!="active" or m.role not in allowed:raise ReviewConflictError(msg)
        return m
    def record_exception(self,user_id,**p):
        self._role(user_id,self.PREP,"authorized assurance tester required")
        return self.repo.add(RegulatoryAssuranceExceptionModel(exception_id=f"rae_{uuid4().hex}",tenant_id=self.tenant_id,status="open",created_by_user_id=user_id,created_at=_now(),**p))
    def aggregate(self,user_id,*,control_id,deficiency_kind,exception_ids,affected_entities,compensating_control,remediation_refs):
        self._role(user_id,self.PREP,"authorized deficiency analyst required")
        known={e.exception_id:e for e in self.repo.exceptions(control_id)}
        selected=[]
        for eid in exception_ids:
            if eid not in known:raise LookupError(f"assurance exception not found: {eid}")
            selected.append(known[eid])
        key=f"{control_id}:{deficiency_kind}"
        versions=self.repo.deficiency_versions(key); version=len(versions)+1
        score=min(100,round(sum(e.severity_score for e in selected)/len(selected)+min(20,max(0,len(selected)-1)*5)))
        body={"key":key,"version":version,"exceptions":sorted(exception_ids),"entities":sorted(set(affected_entities)),"score":score,"compensating_control":compensating_control,"remediation_refs":remediation_refs}
        return self.repo.add(RegulatoryDeficiencyModel(deficiency_id=f"rad_{uuid4().hex}",tenant_id=self.tenant_id,deficiency_key=key,version=version,control_id=control_id,deficiency_kind=deficiency_kind,severity=_severity(score),severity_score=score,exception_ids=exception_ids,affected_entities=sorted(set(affected_entities)),compensating_control=compensating_control,remediation_refs=remediation_refs,repeated_exception_count=len(selected),status="candidate",payload_sha256=_sha(body),created_by_user_id=user_id,created_at=_now()))
    def propose_issue(self,user_id,deficiency_key,rationale):
        self._role(user_id,self.PREP,"authorized issue analyst required"); versions=self.repo.deficiency_versions(deficiency_key)
        if not versions:raise LookupError("deficiency not found")
        d=versions[-1]; candidate=d.severity_score>=85 and (d.repeated_exception_count>=3 or len(d.affected_entities)>=3)
        return self.repo.add(RegulatoryEnterpriseIssueModel(issue_id=f"rei_{uuid4().hex}",tenant_id=self.tenant_id,deficiency_key=deficiency_key,issue_type="enterprise_control_deficiency",candidate_material_weakness=candidate,severity=d.severity,affected_controls=[d.control_id],affected_entities=d.affected_entities,rationale=rationale,sla_due_at=_now()+timedelta(days=7 if d.severity in {"critical","high"} else 30),status="proposed",escalated_by_user_id=None,escalated_at=None,created_at=_now()))
    def escalate(self,user_id,issue_id):
        self._role(user_id,self.ESCALATE,"independent auditor escalation required"); issue=self.repo.issue(issue_id)
        if issue is None:raise LookupError("enterprise assurance issue not found")
        issue.status="escalated";issue.escalated_by_user_id=user_id;issue.escalated_at=_now();self.session.flush();return issue
    def close_deficiency(self,user_id,deficiency_key,*,retest_refs,conclusion,rationale):
        self._role(user_id,self.CLOSE,"independent auditor closure required"); versions=self.repo.deficiency_versions(deficiency_key)
        if not versions:raise LookupError("deficiency not found")
        d=versions[-1]
        if d.created_by_user_id==user_id:raise ReviewConflictError("segregation of duties: deficiency preparer cannot independently close it")
        if conclusion=="remediated" and not retest_refs:raise ReviewConflictError("successful retest evidence is required for remediation closure")
        seq=len(self.repo.closures(deficiency_key))+1
        c=self.repo.add(RegulatoryDeficiencyClosureModel(closure_id=f"rdc_{uuid4().hex}",tenant_id=self.tenant_id,deficiency_key=deficiency_key,closure_version=seq,retest_refs=retest_refs,conclusion=conclusion,rationale=rationale,independent=True,closed_by_user_id=user_id,closed_at=_now()))
        d.status="closed" if conclusion=="remediated" else "open";self.session.flush();return c
    def dashboard(self,user_id):
        self._role(user_id,self.READ,"assurance deficiency read role required"); ds=self.repo.latest_deficiencies();issues=self.repo.issues();now=_now()
        return {"deficiencies":len(ds),"high_or_critical":sum(d.severity in {"high","critical"} for d in ds),"enterprise_issues":len(issues),"escalated":sum(i.status=="escalated" for i in issues),"overdue_sla":sum(i.status not in {"closed","resolved"} and i.sla_due_at<now for i in issues),"material_weakness_candidates":sum(i.candidate_material_weakness for i in issues),"authority":REGULATORY_ASSURANCE_DEFICIENCY_AUTHORITY}
