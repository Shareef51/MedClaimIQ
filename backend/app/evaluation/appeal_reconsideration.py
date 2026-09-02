from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True, slots=True)
class AppealEvaluationExpectation:
    case_id: str
    modality: str
    scenario: str
    expected_changed_fact: str
    expected_recommendation: str
    requires_human_resolution: bool


@dataclass(frozen=True, slots=True)
class AppealEvaluationResult:
    case_id: str
    changed_fact_hit: bool
    recommendation_hit: bool
    citation_coverage_ok: bool
    human_boundary_ok: bool

    @property
    def passed(self) -> bool:
        return all((self.changed_fact_hit, self.recommendation_hit, self.citation_coverage_ok, self.human_boundary_ok))


def load_appeal_evaluation_dataset(path: str | Path) -> tuple[AppealEvaluationExpectation, ...]:
    rows: list[AppealEvaluationExpectation] = []
    for line in Path(path).read_text().splitlines():
        if not line.strip():
            continue
        raw = json.loads(line)
        rows.append(AppealEvaluationExpectation(
            case_id=str(raw["case_id"]), modality=str(raw["modality"]), scenario=str(raw["scenario"]),
            expected_changed_fact=str(raw["expected_changed_fact"]), expected_recommendation=str(raw["expected_recommendation"]),
            requires_human_resolution=bool(raw["requires_human_resolution"]),
        ))
    return tuple(rows)


def evaluate_appeal_output(expectation: AppealEvaluationExpectation, *, changed_facts: Iterable[str], recommendation: str,
                           citations_present: int, selected_items: int, adjudication_authority: str,
                           requires_human_review: bool) -> AppealEvaluationResult:
    changed = {str(value).lower() for value in changed_facts}
    citation_coverage = citations_present / max(1, selected_items)
    return AppealEvaluationResult(
        case_id=expectation.case_id,
        changed_fact_hit=expectation.expected_changed_fact.lower() in changed,
        recommendation_hit=recommendation == expectation.expected_recommendation,
        citation_coverage_ok=citation_coverage >= 0.95,
        human_boundary_ok=(not expectation.requires_human_resolution) or (adjudication_authority == "none" and requires_human_review),
    )


def aggregate_appeal_eval(results: Iterable[AppealEvaluationResult]) -> dict[str, float | int]:
    values = tuple(results)
    total = len(values)
    if total == 0:
        return {"cases": 0, "pass_rate": 0.0, "human_boundary_rate": 0.0}
    return {
        "cases": total,
        "pass_rate": sum(item.passed for item in values) / total,
        "human_boundary_rate": sum(item.human_boundary_ok for item in values) / total,
    }
