import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"backend"))
from app.services.evaluation import evaluation_model_contract,load_dataset,load_policy
from app.evaluation.harness import GoldenEvaluationHarness
assert len(evaluation_model_contract()["metrics"])>=20
for name in ("golden_claims_v1","adversarial_v1","agent_v1"):
    d=load_dataset(name);s=GoldenEvaluationHarness(load_policy()).run(d,"verification",d.get("baseline_metrics"));assert s.decision.value=="pass",s.regression_reasons
m=(ROOT/"backend/alembic/versions/0019_ai_evaluation_quality.py").read_text();assert "FORCE ROW LEVEL SECURITY" in m and "evaluation_release_gates" in m and "_immutable" in m
print("AI/RAG evaluation quality architecture verified")
