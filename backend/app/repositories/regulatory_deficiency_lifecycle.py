from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import set_tenant_context
from app.models.regulatory_deficiency_lifecycle import *

class RegulatoryDeficiencyLifecycleRepository:
    def __init__(self,session:Session,tenant_id:str): self.session=session; self.tenant_id=tenant_id; set_tenant_context(session,tenant_id)
    def add(self,row):
        if row.tenant_id != self.tenant_id: raise ValueError("tenant mismatch")
        self.session.add(row); self.session.flush(); return row
    def investigations(self): return list(self.session.scalars(select(RegulatoryDeficiencyInvestigationModel).where(RegulatoryDeficiencyInvestigationModel.tenant_id==self.tenant_id).order_by(RegulatoryDeficiencyInvestigationModel.created_at.desc())))
    def dispositions(self,key): return list(self.session.scalars(select(RegulatoryDeficiencyDispositionModel).where(RegulatoryDeficiencyDispositionModel.tenant_id==self.tenant_id,RegulatoryDeficiencyDispositionModel.deficiency_key==key).order_by(RegulatoryDeficiencyDispositionModel.version)))
    def plans(self,key=None):
        q=select(RegulatoryCorrectiveActionPlanModel).where(RegulatoryCorrectiveActionPlanModel.tenant_id==self.tenant_id)
        if key: q=q.where(RegulatoryCorrectiveActionPlanModel.deficiency_key==key)
        return list(self.session.scalars(q.order_by(RegulatoryCorrectiveActionPlanModel.created_at.desc())))
    def plan(self,plan_id): return self.session.scalar(select(RegulatoryCorrectiveActionPlanModel).where(RegulatoryCorrectiveActionPlanModel.tenant_id==self.tenant_id,RegulatoryCorrectiveActionPlanModel.plan_id==plan_id))
    def attestations(self,key): return list(self.session.scalars(select(RegulatoryExecutiveAttestationModel).where(RegulatoryExecutiveAttestationModel.tenant_id==self.tenant_id,RegulatoryExecutiveAttestationModel.deficiency_key==key).order_by(RegulatoryExecutiveAttestationModel.version)))
