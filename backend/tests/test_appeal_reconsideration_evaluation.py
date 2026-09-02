from pathlib import Path
from app.evaluation.appeal_reconsideration import aggregate_appeal_eval, evaluate_appeal_output, load_appeal_evaluation_dataset


def test_release38_evaluation_dataset_is_multimodal_and_human_bound():
    rows=load_appeal_evaluation_dataset(Path("../sample-data/evaluation/appeal_reconsideration_cases.jsonl"))
    assert len(rows)>=5
    assert {x.modality for x in rows}>={"document","image","audio","video","fhir"}
    assert all(x.requires_human_resolution for x in rows)


def test_release38_evaluator_scores_citations_recommendation_changed_fact_and_authority():
    row=load_appeal_evaluation_dataset(Path("../sample-data/evaluation/appeal_reconsideration_cases.jsonl"))[0]
    result=evaluate_appeal_output(row,changed_facts=["amount"],recommendation="consider_modify",citations_present=8,selected_items=8,adjudication_authority="none",requires_human_review=True)
    summary=aggregate_appeal_eval([result])
    assert result.passed and summary["pass_rate"]==1.0 and summary["human_boundary_rate"]==1.0
