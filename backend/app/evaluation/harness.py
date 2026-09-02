from __future__ import annotations
from dataclasses import asdict, dataclass, replace
from statistics import mean
from typing import Any
from uuid import uuid4
from app.evaluation.domain import CaseResult,EvaluationSummary,GateDecision,MetricResult,stable_hash
from app.evaluation.metrics import citation_exactness,field_accuracy,ndcg_at_k,percentile,precision_at_k,recall_at_k,reciprocal_rank,safe_div,token_f1,unsupported_claim_rate

@dataclass(frozen=True, slots=True)
class EvaluationPolicy:
    thresholds:dict[str,float]; max_regression:dict[str,float]; cost_per_1k_input_usd:float=0.0; cost_per_1k_output_usd:float=0.0; zero_tolerance_suites:tuple[str,...]=()

class GoldenEvaluationHarness:
    """Deterministic metrics/release gate over versioned synthetic golden observations."""
    def __init__(self,policy:EvaluationPolicy):self.policy=policy
    def _threshold(self,name):return self.policy.thresholds.get(name)
    def evaluate_case(self,case:dict[str,Any])->CaseResult:
        suite=str(case["suite"]); exp=case.get("expected",{}); obs=case.get("observed",{}); metrics=[]; reasons=[]
        def add(name,value,higher=True):
            m=MetricResult(name,round(float(value),6),self._threshold(name),higher,suite); metrics.append(m)
            if not m.passed:reasons.append(f"{name}={m.value} threshold={m.threshold}")
        if suite=="extraction":
            add("extraction_field_accuracy",field_accuracy(exp.get("fields",{}),obs.get("fields",{})))
            if "text" in exp:add("ocr_token_f1",token_f1(str(exp["text"]),str(obs.get("text",""))))
            if "table" in exp:add("table_cell_accuracy",field_accuracy(exp["table"],obs.get("table",{})))
        elif suite=="retrieval":
            ranked=list(obs.get("ranked_evidence_ids",[])); expected=list(exp.get("evidence_ids",[])); k=int(case.get("k",5))
            add("retrieval_recall_at_k",recall_at_k(expected,ranked,k)); add("retrieval_precision_at_k",precision_at_k(expected,ranked,k)); add("retrieval_mrr",reciprocal_rank(expected,ranked)); add("reranker_ndcg_at_k",ndcg_at_k(expected,ranked,k))
        elif suite=="citation":add("citation_exactness",citation_exactness(exp.get("citations",[]),obs.get("citations",[])))
        elif suite=="grounding":
            rate=unsupported_claim_rate(list(obs.get("claims",[]))); add("groundedness",1-rate); add("unsupported_claim_rate",rate,False)
        elif suite=="security":add("prompt_injection_resistance",1.0 if bool(exp.get("blocked"))==bool(obs.get("blocked")) else 0.0)
        elif suite=="agents":
            ek=set(exp.get("evidence_keys",[])); ok=set(obs.get("evidence_keys",[])); add("agent_structured_output_accuracy",1.0 if bool(obs.get("schema_valid")) and obs.get("disposition")==exp.get("disposition") else 0.0); add("agent_evidence_key_accuracy",safe_div(len(ek&ok),len(ek|ok)) if ek|ok else 1.0)
        elif suite=="workflow":add("workflow_route_accuracy",1.0 if list(obs.get("route",[]))==list(exp.get("route",[])) else 0.0)
        elif suite=="tools":
            allowed=set(exp.get("allowed_tools",[])); called=set(obs.get("called_tools",[])); denied=set(obs.get("denied_tools",[])); must=set(exp.get("must_deny",[])); add("tool_policy_compliance",1.0 if called.issubset(allowed) and must.issubset(denied) else 0.0)
        elif suite=="escalation":add("human_escalation_accuracy",1.0 if bool(obs.get("escalated"))==bool(exp.get("escalated")) else 0.0)
        elif suite=="fhir":add("fhir_match_accuracy",1.0 if obs.get("match_status")==exp.get("match_status") else 0.0)
        elif suite=="contradiction":add("contradiction_detection_accuracy",1.0 if bool(obs.get("detected"))==bool(exp.get("detected")) and obs.get("severity")==exp.get("severity") else 0.0)
        elif suite!="performance":reasons.append("unknown_suite")
        latency=float(obs.get("latency_ms",0)); inp=int(obs.get("input_tokens",0)); out=int(obs.get("output_tokens",0)); cost=(inp/1000)*self.policy.cost_per_1k_input_usd+(out/1000)*self.policy.cost_per_1k_output_usd
        return CaseResult(str(case["case_id"]),suite,not reasons,tuple(metrics),tuple(reasons),latency,inp,out,round(cost,8))
    def run(self,dataset:dict[str,Any],candidate_version:str,baseline:dict[str,float]|None=None)->EvaluationSummary:
        cases=tuple(self.evaluate_case(c) for c in dataset["cases"]); grouped={}
        for c in cases:
            for m in c.metrics:grouped.setdefault(m.metric,[]).append(m.value)
        metrics=[MetricResult(n,round(mean(v),6),self._threshold(n),n!="unsupported_claim_rate","aggregate") for n,v in sorted(grouped.items())]
        lats=[c.latency_ms for c in cases if c.latency_ms>0]; costs=[c.estimated_cost_usd for c in cases]
        if lats:metrics += [MetricResult("latency_p50_ms",percentile(lats,50),self._threshold("latency_p50_ms"),False,"performance"),MetricResult("latency_p95_ms",percentile(lats,95),self._threshold("latency_p95_ms"),False,"performance")]
        metrics.append(MetricResult("mean_cost_usd",round(mean(costs),8) if costs else 0,self._threshold("mean_cost_usd"),False,"performance"))
        metrics.append(MetricResult("case_pass_rate",round(safe_div(sum(c.passed for c in cases),len(cases)),6),self._threshold("case_pass_rate"),True,"aggregate"))
        reasons=[]
        if baseline:
            metrics=[replace(m,details={**m.details,"baseline_value":float(baseline[m.metric]),"delta":round(m.value-float(baseline[m.metric]),6)}) if m.metric in baseline else m for m in metrics]
            for m in metrics:
                if m.metric in baseline and m.metric in self.policy.max_regression:
                    deg=(float(baseline[m.metric])-m.value) if m.higher_is_better else (m.value-float(baseline[m.metric])); allowed=self.policy.max_regression[m.metric]
                    if deg>allowed:reasons.append(f"{m.metric} regressed by {deg:.6f} > {allowed:.6f}")
        critical_failed=[c.case_id for c in cases if (not c.passed and c.suite in self.policy.zero_tolerance_suites)]
        if critical_failed:reasons.append("zero-tolerance case failures: "+", ".join(sorted(critical_failed)))
        failed=[m.metric for m in metrics if not m.passed]
        if failed:reasons.append("threshold failures: "+", ".join(sorted(failed)))
        return EvaluationSummary(f"eval-{uuid4()}",str(dataset["dataset_version"]),candidate_version,str(dataset.get("baseline_version")) if baseline else None,cases,tuple(metrics),GateDecision.BLOCK if reasons else GateDecision.PASS,tuple(reasons),stable_hash({"policy":asdict(self.policy),"dataset_version":dataset["dataset_version"]}))
