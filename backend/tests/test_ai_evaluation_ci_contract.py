from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def test_ci_runs_both_golden_and_adversarial_gates():
    t=(ROOT/'.github/workflows/ai-quality-gate.yml').read_text(); assert '--dataset golden_claims_v1' in t; assert '--dataset adversarial_v1' in t; assert '--gate' in t; assert 'upload-artifact' in t
def test_eval_cli_and_docs_exist():
    assert (ROOT/'scripts/run_evaluations.py').exists(); assert (ROOT/'docs/AI_RAG_EVALUATION_QUALITY.md').exists()
