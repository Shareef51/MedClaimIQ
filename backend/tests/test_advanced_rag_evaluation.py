from __future__ import annotations
import json
from pathlib import Path
from app.evaluation.advanced_rag import AdvancedRAGEvaluationHarness

ROOT=Path(__file__).resolve().parents[2]

def test_advanced_rag_deterministic_evaluation_gate_passes():
    dataset=json.loads((ROOT/'sample-data/advanced_rag_eval_v1.json').read_text())
    result=AdvancedRAGEvaluationHarness().run(dataset)
    assert result.decision == 'pass', result.reasons
    assert result.metrics['metadata_filter_safety'] == 1.0
    assert result.metrics['agent_domain_safety'] == 1.0
