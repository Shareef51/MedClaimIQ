from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import set_tenant_context
from app.models.regulatory_remediation import *

class RegulatoryRemediationRepository:
    def __init__(self,session:Session,tenant_id:str):self.session=session;self.tenant_id=tenant_id;set_tenant_context(session,tenant_id)
    def add(self,row):
        if row.tenant_id!=self.tenant_id:raise ValueError("tenant mismatch")
        self.session.add(row);self.session.flush();return row
    def plan(self,plan_id,for_update=False):
        q=select(RegulatoryRemediationPlanModel).where(RegulatoryRemediationPlanModel.tenant_id==self.tenant_id,RegulatoryRemediationPlanModel.plan_id==plan_id)
        if for_update:q=q.with_for_update()
        return self.session.scalar(q)
    def plans(self):return list(self.session.scalars(select(RegulatoryRemediationPlanModel).where(RegulatoryRemediationPlanModel.tenant_id==self.tenant_id).order_by(RegulatoryRemediationPlanModel.updated_at.desc())))
    def plans_for_case(self,case_id):return list(self.session.scalars(select(RegulatoryRemediationPlanModel).where(RegulatoryRemediationPlanModel.tenant_id==self.tenant_id,RegulatoryRemediationPlanModel.examination_case_id==case_id).order_by(RegulatoryRemediationPlanModel.plan_version)))
    def plans_for_finding(self,finding_id):return list(self.session.scalars(select(RegulatoryRemediationPlanModel).where(RegulatoryRemediationPlanModel.tenant_id==self.tenant_id,RegulatoryRemediationPlanModel.finding_id==finding_id).order_by(RegulatoryRemediationPlanModel.plan_version)))
    def tasks(self,plan_id):return list(self.session.scalars(select(RegulatoryRemediationTaskModel).where(RegulatoryRemediationTaskModel.tenant_id==self.tenant_id,RegulatoryRemediationTaskModel.plan_id==plan_id).order_by(RegulatoryRemediationTaskModel.due_at)))
    def task(self,plan_id,task_key):return self.session.scalar(select(RegulatoryRemediationTaskModel).where(RegulatoryRemediationTaskModel.tenant_id==self.tenant_id,RegulatoryRemediationTaskModel.plan_id==plan_id,RegulatoryRemediationTaskModel.task_key==task_key))
    def checkpoints(self,plan_id):return list(self.session.scalars(select(RegulatoryRemediationCheckpointModel).where(RegulatoryRemediationCheckpointModel.tenant_id==self.tenant_id,RegulatoryRemediationCheckpointModel.plan_id==plan_id).order_by(RegulatoryRemediationCheckpointModel.locked_at)))
    def retests(self,plan_id):return list(self.session.scalars(select(RegulatoryControlRetestModel).where(RegulatoryControlRetestModel.tenant_id==self.tenant_id,RegulatoryControlRetestModel.plan_id==plan_id).order_by(RegulatoryControlRetestModel.retested_at)))
    def waivers(self,plan_id):return list(self.session.scalars(select(RegulatoryRemediationWaiverModel).where(RegulatoryRemediationWaiverModel.tenant_id==self.tenant_id,RegulatoryRemediationWaiverModel.plan_id==plan_id).order_by(RegulatoryRemediationWaiverModel.created_at)))
    def waiver(self,plan_id,key):return self.session.scalar(select(RegulatoryRemediationWaiverModel).where(RegulatoryRemediationWaiverModel.tenant_id==self.tenant_id,RegulatoryRemediationWaiverModel.plan_id==plan_id,RegulatoryRemediationWaiverModel.waiver_key==key))
    def followups(self,plan_id):return list(self.session.scalars(select(RegulatoryRemediationFollowupModel).where(RegulatoryRemediationFollowupModel.tenant_id==self.tenant_id,RegulatoryRemediationFollowupModel.plan_id==plan_id).order_by(RegulatoryRemediationFollowupModel.response_version)))
    def certifications(self,plan_id):return list(self.session.scalars(select(RegulatoryRemediationClosureCertificationModel).where(RegulatoryRemediationClosureCertificationModel.tenant_id==self.tenant_id,RegulatoryRemediationClosureCertificationModel.plan_id==plan_id).order_by(RegulatoryRemediationClosureCertificationModel.certification_sequence)))
    def audit(self,plan_id):return list(self.session.scalars(select(RegulatoryRemediationAuditEventModel).where(RegulatoryRemediationAuditEventModel.tenant_id==self.tenant_id,RegulatoryRemediationAuditEventModel.plan_id==plan_id).order_by(RegulatoryRemediationAuditEventModel.sequence)))
