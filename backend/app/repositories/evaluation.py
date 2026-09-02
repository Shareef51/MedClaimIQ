from __future__ import annotations
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.evaluation.domain import EvaluationSummary
from app.models.evaluation import EvaluationBaselineModel,EvaluationCaseModel,EvaluationMetricModel,EvaluationReleaseGateModel,EvaluationRunModel
class EvaluationRepository:
    def __init__(self,session:Session,tenant_id:str):self.session=session;self.tenant_id=tenant_id
    def persist_summary(self,summary:EvaluationSummary,*,trace_id,started_at,completed_at,report_sha256:str):
        run=EvaluationRunModel(run_id=summary.run_id,tenant_id=self.tenant_id,dataset_version=summary.dataset_version,candidate_version=summary.candidate_version,baseline_version=summary.baseline_version,decision=summary.decision.value,config_sha256=summary.config_sha256,case_count=len(summary.cases),pass_rate=summary.pass_rate,regression_reasons=list(summary.regression_reasons),trace_id=trace_id,started_at=started_at,completed_at=completed_at); self.session.add(run)
        for m in summary.metrics:self.session.add(EvaluationMetricModel(metric_id=f"evalm-{uuid4()}",tenant_id=self.tenant_id,run_id=run.run_id,metric=m.metric,suite=m.suite,value=m.value,threshold=m.threshold,higher_is_better=m.higher_is_better,passed=m.passed))
        for c in summary.cases:self.session.add(EvaluationCaseModel(result_id=f"evalc-{uuid4()}",tenant_id=self.tenant_id,run_id=run.run_id,case_id=c.case_id,suite=c.suite,passed=c.passed,reasons=list(c.reasons),latency_ms=c.latency_ms,input_tokens=c.input_tokens,output_tokens=c.output_tokens,estimated_cost_usd=c.estimated_cost_usd))
        self.session.add(EvaluationReleaseGateModel(gate_id=f"evalg-{uuid4()}",tenant_id=self.tenant_id,run_id=run.run_id,decision=summary.decision.value,reasons=list(summary.regression_reasons),policy_sha256=summary.config_sha256,immutable_report_sha256=report_sha256)); self.session.flush(); return run
    def active_baseline(self,dataset_version:str):return self.session.scalar(select(EvaluationBaselineModel).where(EvaluationBaselineModel.tenant_id==self.tenant_id,EvaluationBaselineModel.dataset_version==dataset_version,EvaluationBaselineModel.active.is_(True)).order_by(EvaluationBaselineModel.created_at.desc()))
    def list_runs(self,limit:int=25):return list(self.session.scalars(select(EvaluationRunModel).where(EvaluationRunModel.tenant_id==self.tenant_id).order_by(EvaluationRunModel.created_at.desc()).limit(limit)))
