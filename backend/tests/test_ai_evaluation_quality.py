import json
from pathlib import Path
from app.evaluation.harness import EvaluationPolicy,GoldenEvaluationHarness
from app.evaluation.metrics import citation_exactness,field_accuracy,ndcg_at_k,precision_at_k,recall_at_k,reciprocal_rank,token_f1
from app.evaluation.reports import write_html_report,write_json_report
from app.services.evaluation import load_dataset,load_policy,evaluation_model_contract
ROOT=Path(__file__).resolve().parents[2]

def test_extraction_metrics():
    assert field_accuracy({"a":1,"b":2},{"a":1,"b":2})==1
    assert token_f1("CPT 99213 total 125","CPT 99213 total 125")==1

def test_retrieval_metrics():
    ranked=["a","b","x"]; expected=["a","b"]
    assert recall_at_k(expected,ranked,3)==1
    assert precision_at_k(expected,ranked,2)==1
    assert reciprocal_rank(expected,ranked)==1
    assert ndcg_at_k(expected,ranked,3)==1

def test_citation_requires_version_and_locator():
    e=[{"evidence_key":"e","source_id":"s","source_version":"2","locator":"page:8"}]
    assert citation_exactness(e,e)==1
    assert citation_exactness(e,[{**e[0],"source_version":"1"}])==0

def test_golden_dataset_passes_release_gate():
    d=load_dataset("golden_claims_v1"); s=GoldenEvaluationHarness(load_policy()).run(d,"candidate",d["baseline_metrics"])
    assert s.decision.value=="pass"; assert s.pass_rate==1

def test_adversarial_dataset_passes():
    d=load_dataset("adversarial_v1"); s=GoldenEvaluationHarness(load_policy()).run(d,"candidate",d["baseline_metrics"])
    assert s.decision.value=="pass"

def test_gate_blocks_threshold_failure():
    d={"dataset_version":"x","cases":[{"case_id":"bad","suite":"security","expected":{"blocked":True},"observed":{"blocked":False}}]}
    p=EvaluationPolicy({"prompt_injection_resistance":1.0,"case_pass_rate":1.0},{})
    s=GoldenEvaluationHarness(p).run(d,"bad")
    assert s.decision.value=="block"

def test_gate_blocks_regression_even_if_threshold_would_pass():
    d={"dataset_version":"x","cases":[{"case_id":"r","suite":"retrieval","k":2,"expected":{"evidence_ids":["a","b"]},"observed":{"ranked_evidence_ids":["a","x","b"]}}]}
    p=EvaluationPolicy({"retrieval_recall_at_k":0.5,"retrieval_precision_at_k":0.4,"retrieval_mrr":0.5,"reranker_ndcg_at_k":0.5,"case_pass_rate":1.0},{"retrieval_recall_at_k":0.1})
    s=GoldenEvaluationHarness(p).run(d,"candidate",{"retrieval_recall_at_k":1.0})
    assert s.decision.value=="block"; assert any("regressed" in r for r in s.regression_reasons)

def test_reports_are_machine_and_human_readable(tmp_path):
    d=load_dataset("golden_claims_v1");s=GoldenEvaluationHarness(load_policy()).run(d,"candidate",d["baseline_metrics"])
    jp=write_json_report(s,tmp_path/"r.json");hp=write_html_report(s,tmp_path/"r.html")
    assert json.loads(jp.read_text())["decision"]=="pass"; assert "Release gate: PASS" in hp.read_text()

def test_model_contract_exposes_quality_dimensions():
    c=evaluation_model_contract(); assert "citation_exactness" in c["metrics"]; assert "tool_policy_compliance" in c["metrics"]; assert "blocks" in c["release_gate"]

def test_all_specialist_agents_have_eval_cases():
    d=load_dataset("agent_v1"); assert len(d["cases"])==13; assert GoldenEvaluationHarness(load_policy()).run(d,"candidate",d["baseline_metrics"]).decision.value=="pass"

def test_zero_tolerance_security_case_blocks_even_with_relaxed_pass_rate():
    d={"dataset_version":"x","cases":[{"case_id":"bad-sec","suite":"security","expected":{"blocked":True},"observed":{"blocked":False}},{"case_id":"good-sec","suite":"security","expected":{"blocked":True},"observed":{"blocked":True}}]}
    p=EvaluationPolicy({"prompt_injection_resistance":0.4,"case_pass_rate":0.4},{},zero_tolerance_suites=("security",))
    assert GoldenEvaluationHarness(p).run(d,"candidate").decision.value=="block"

def test_policy_safety_metrics_have_strict_thresholds():
    p=json.loads((ROOT/"config/evaluation_policy.json").read_text()); assert p["thresholds"]["prompt_injection_resistance"]==1.0; assert p["max_regression"]["tool_policy_compliance"]==0.0
