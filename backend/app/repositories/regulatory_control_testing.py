from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import set_tenant_context
from app.models.regulatory_control_testing import *

class RegulatoryControlTestingRepository:
    def __init__(self,session:Session,tenant_id:str):self.session=session;self.tenant_id=tenant_id;set_tenant_context(session,tenant_id)
    def add(self,row):
        if row.tenant_id!=self.tenant_id:raise ValueError("tenant mismatch")
        self.session.add(row);self.session.flush();return row
    def plan(self,test_plan_id):return self.session.scalar(select(RegulatoryControlTestPlanModel).where(RegulatoryControlTestPlanModel.tenant_id==self.tenant_id,RegulatoryControlTestPlanModel.test_plan_id==test_plan_id))
    def plans(self):return list(self.session.scalars(select(RegulatoryControlTestPlanModel).where(RegulatoryControlTestPlanModel.tenant_id==self.tenant_id).order_by(RegulatoryControlTestPlanModel.created_at.desc())))
    def run(self,test_run_id):return self.session.scalar(select(RegulatoryControlTestRunModel).where(RegulatoryControlTestRunModel.tenant_id==self.tenant_id,RegulatoryControlTestRunModel.test_run_id==test_run_id))
    def runs(self):return list(self.session.scalars(select(RegulatoryControlTestRunModel).where(RegulatoryControlTestRunModel.tenant_id==self.tenant_id).order_by(RegulatoryControlTestRunModel.created_at.desc())))
    def sample(self,sample_id):return self.session.scalar(select(RegulatoryEvidenceSampleModel).where(RegulatoryEvidenceSampleModel.tenant_id==self.tenant_id,RegulatoryEvidenceSampleModel.sample_id==sample_id))
    def samples(self,test_run_id):return list(self.session.scalars(select(RegulatoryEvidenceSampleModel).where(RegulatoryEvidenceSampleModel.tenant_id==self.tenant_id,RegulatoryEvidenceSampleModel.test_run_id==test_run_id).order_by(RegulatoryEvidenceSampleModel.risk_score.desc())))
    def conclusions(self,test_run_id):return list(self.session.scalars(select(RegulatoryControlTestConclusionModel).where(RegulatoryControlTestConclusionModel.tenant_id==self.tenant_id,RegulatoryControlTestConclusionModel.test_run_id==test_run_id).order_by(RegulatoryControlTestConclusionModel.conclusion_version)))
