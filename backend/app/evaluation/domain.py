from __future__ import annotations
from dataclasses import dataclass, field
from enum import StrEnum
from hashlib import sha256
from typing import Any

class EvaluationSuite(StrEnum):
    EXTRACTION="extraction"; RETRIEVAL="retrieval"; CITATION="citation"; GROUNDING="grounding"; SECURITY="security"; AGENTS="agents"; WORKFLOW="workflow"; TOOLS="tools"; ESCALATION="escalation"; FHIR="fhir"; CONTRADICTION="contradiction"; PERFORMANCE="performance"
class GateDecision(StrEnum): PASS="pass"; BLOCK="block"

@dataclass(frozen=True, slots=True)
class MetricResult:
    metric:str; value:float; threshold:float|None=None; higher_is_better:bool=True; suite:str=""; numerator:int|None=None; denominator:int|None=None; details:dict[str,Any]=field(default_factory=dict)
    @property
    def passed(self)->bool:
        if self.threshold is None: return True
        return self.value >= self.threshold if self.higher_is_better else self.value <= self.threshold
@dataclass(frozen=True, slots=True)
class CaseResult:
    case_id:str; suite:str; passed:bool; metrics:tuple[MetricResult,...]=(); reasons:tuple[str,...]=(); latency_ms:float=0.0; input_tokens:int=0; output_tokens:int=0; estimated_cost_usd:float=0.0
@dataclass(frozen=True, slots=True)
class EvaluationSummary:
    run_id:str; dataset_version:str; candidate_version:str; baseline_version:str|None; cases:tuple[CaseResult,...]; metrics:tuple[MetricResult,...]; decision:GateDecision; regression_reasons:tuple[str,...]; config_sha256:str
    @property
    def pass_rate(self)->float: return sum(1 for c in self.cases if c.passed)/len(self.cases) if self.cases else 0.0

def stable_hash(value:object)->str:
    import json
    return sha256(json.dumps(value,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()
