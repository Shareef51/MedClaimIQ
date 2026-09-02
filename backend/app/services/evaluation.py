from __future__ import annotations
import json
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
from app.evaluation.harness import EvaluationPolicy,GoldenEvaluationHarness
from app.evaluation.reports import summary_to_dict
from app.repositories.evaluation import EvaluationRepository
ROOT=Path(__file__).resolve().parents[3]
def load_policy():
    raw=json.loads((ROOT/"config/evaluation_policy.json").read_text());return EvaluationPolicy(raw["thresholds"],raw["max_regression"],raw["cost_model"]["input_per_1k_usd"],raw["cost_model"]["output_per_1k_usd"],tuple(raw.get("zero_tolerance_suites",[])))
def load_dataset(name:str):
    allowed={"golden_claims_v1":"golden_claims_v1.json","adversarial_v1":"adversarial_evaluation_v1.json","agent_v1":"agent_evaluation_v1.json"}
    if name not in allowed:raise ValueError("unknown evaluation dataset")
    return json.loads((ROOT/"sample-data"/allowed[name]).read_text())
def evaluation_model_contract():return {"quality_boundary":"deterministic golden labels and versioned thresholds","datasets":["golden_claims_v1","adversarial_v1","agent_v1"],"metrics":["extraction_field_accuracy","ocr_token_f1","table_cell_accuracy","retrieval_recall_at_k","retrieval_precision_at_k","retrieval_mrr","reranker_ndcg_at_k","citation_exactness","groundedness","unsupported_claim_rate","prompt_injection_resistance","agent_structured_output_accuracy","agent_evidence_key_accuracy","workflow_route_accuracy","tool_policy_compliance","human_escalation_accuracy","fhir_match_accuracy","contradiction_detection_accuracy","latency_p50_ms","latency_p95_ms","mean_cost_usd","case_pass_rate"],"release_gate":"release gate blocks on threshold failure or baseline regression beyond tolerance","privacy":"synthetic/de-identified eval data only; reports contain metrics/hashes"}
class EvaluationService:
    def __init__(self,repository):self.repository=repository
    def run(self,*,dataset_name,candidate_version,trace_id=None):
        started=datetime.now(timezone.utc); dataset=load_dataset(dataset_name); bm=self.repository.active_baseline(str(dataset["dataset_version"])); baseline=bm.metrics if bm else dataset.get("baseline_metrics"); summary=GoldenEvaluationHarness(load_policy()).run(dataset,candidate_version,baseline); blob=json.dumps(summary_to_dict(summary),sort_keys=True,default=str).encode(); completed=datetime.now(timezone.utc); self.repository.persist_summary(summary,trace_id=trace_id,started_at=started,completed_at=completed,report_sha256=sha256(blob).hexdigest()); return summary
