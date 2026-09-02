from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import set_tenant_context
from app.models.regulatory_assurance_deficiencies import *

class RegulatoryAssuranceDeficiencyRepository:
    def __init__(self,session:Session,tenant_id:str):self.session=session;self.tenant_id=tenant_id;set_tenant_context(session,tenant_id)
    def add(self,row):
        if row.tenant_id!=self.tenant_id:raise ValueError("tenant mismatch")
        self.session.add(row);self.session.flush();return row
    def exceptions(self,control_id=None):
        q=select(RegulatoryAssuranceExceptionModel).where(RegulatoryAssuranceExceptionModel.tenant_id==self.tenant_id)
        if control_id:q=q.where(RegulatoryAssuranceExceptionModel.control_id==control_id)
        return list(self.session.scalars(q.order_by(RegulatoryAssuranceExceptionModel.created_at.desc())))
    def deficiency_versions(self,key):return list(self.session.scalars(select(RegulatoryDeficiencyModel).where(RegulatoryDeficiencyModel.tenant_id==self.tenant_id,RegulatoryDeficiencyModel.deficiency_key==key).order_by(RegulatoryDeficiencyModel.version)))
    def latest_deficiencies(self):
        rows=list(self.session.scalars(select(RegulatoryDeficiencyModel).where(RegulatoryDeficiencyModel.tenant_id==self.tenant_id).order_by(RegulatoryDeficiencyModel.created_at.desc())))
        out={}
        for r in rows: out.setdefault(r.deficiency_key,r)
        return list(out.values())
    def issue(self,issue_id):return self.session.scalar(select(RegulatoryEnterpriseIssueModel).where(RegulatoryEnterpriseIssueModel.tenant_id==self.tenant_id,RegulatoryEnterpriseIssueModel.issue_id==issue_id))
    def issues(self):return list(self.session.scalars(select(RegulatoryEnterpriseIssueModel).where(RegulatoryEnterpriseIssueModel.tenant_id==self.tenant_id).order_by(RegulatoryEnterpriseIssueModel.created_at.desc())))
    def closures(self,key):return list(self.session.scalars(select(RegulatoryDeficiencyClosureModel).where(RegulatoryDeficiencyClosureModel.tenant_id==self.tenant_id,RegulatoryDeficiencyClosureModel.deficiency_key==key).order_by(RegulatoryDeficiencyClosureModel.closure_version)))
