from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import set_tenant_context
from app.models.regulatory_closure_governance import *

class RegulatoryClosureGovernanceRepository:
    def __init__(self,session:Session,tenant_id:str): self.session=session; self.tenant_id=tenant_id; set_tenant_context(session,tenant_id)
    def add(self,row):
        if row.tenant_id != self.tenant_id: raise ValueError("tenant mismatch")
        self.session.add(row); self.session.flush(); return row
    def packages(self,key=None):
        q=select(RegulatoryClosurePackageModel).where(RegulatoryClosurePackageModel.tenant_id==self.tenant_id)
        if key: q=q.where(RegulatoryClosurePackageModel.deficiency_key==key)
        return list(self.session.scalars(q.order_by(RegulatoryClosurePackageModel.created_at.desc())))
    def package(self,pid): return self.session.scalar(select(RegulatoryClosurePackageModel).where(RegulatoryClosurePackageModel.tenant_id==self.tenant_id,RegulatoryClosurePackageModel.package_id==pid))
    def certifications(self,key): return list(self.session.scalars(select(RegulatoryClosureCertificationModel).where(RegulatoryClosureCertificationModel.tenant_id==self.tenant_id,RegulatoryClosureCertificationModel.deficiency_key==key).order_by(RegulatoryClosureCertificationModel.version)))
    def windows(self,key=None):
        q=select(RegulatorySustainabilityWindowModel).where(RegulatorySustainabilityWindowModel.tenant_id==self.tenant_id)
        if key: q=q.where(RegulatorySustainabilityWindowModel.deficiency_key==key)
        return list(self.session.scalars(q.order_by(RegulatorySustainabilityWindowModel.created_at.desc())))
    def window(self,wid): return self.session.scalar(select(RegulatorySustainabilityWindowModel).where(RegulatorySustainabilityWindowModel.tenant_id==self.tenant_id,RegulatorySustainabilityWindowModel.window_id==wid))
    def reopen_decisions(self,key=None):
        q=select(RegulatoryReopenDecisionModel).where(RegulatoryReopenDecisionModel.tenant_id==self.tenant_id)
        if key: q=q.where(RegulatoryReopenDecisionModel.deficiency_key==key)
        return list(self.session.scalars(q.order_by(RegulatoryReopenDecisionModel.decided_at.desc())))
