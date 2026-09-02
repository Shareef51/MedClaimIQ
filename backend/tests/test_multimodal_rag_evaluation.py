from __future__ import annotations
import json
from pathlib import Path
from app.evaluation.multimodal_rag import MultimodalRAGEvaluationHarness

ROOT=Path(__file__).resolve().parents[2]

def test_multimodal_rag_deterministic_quality_gate_passes():
    data=json.loads((ROOT/'sample-data/multimodal_rag_eval_v1.json').read_text())
    result=MultimodalRAGEvaluationHarness().run(data)
    assert result.decision=='pass', result.reasons
    assert result.metrics['citation_anchor_accuracy']==1.0
    assert result.metrics['inconsistency_detection']==1.0
    assert result.metrics['knowledge_gap_accuracy']==1.0
