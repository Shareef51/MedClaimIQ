from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from app.domain.multimodal_rag import EvidenceModality, InconsistencySeverity, MultimodalCandidate, MultimodalCitation
from app.domain.rag import RAGDomain
from app.rag.multimodal_gap import MultimodalGapDetector
from app.rag.multimodal_routing import MultimodalRouter
from app.rag.multimodal_verification import CrossModalVerifier


@dataclass(frozen=True, slots=True)
class MultimodalEvalCase:
    case_id: str
    passed: bool
    metrics: dict[str, float]
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class MultimodalEvalSummary:
    dataset_version: str
    decision: str
    metrics: dict[str, float]
    cases: tuple[MultimodalEvalCase, ...]
    reasons: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "dataset_version": self.dataset_version,
            "decision": self.decision,
            "metrics": self.metrics,
            "reasons": list(self.reasons),
            "cases": [{**asdict(c), "reasons": list(c.reasons)} for c in self.cases],
        }


class MultimodalRAGEvaluationHarness:
    def __init__(self) -> None:
        self.thresholds = {
            "routing_accuracy": 1.0,
            "required_modality_safety": 1.0,
            "citation_anchor_accuracy": 1.0,
            "inconsistency_detection": 1.0,
            "knowledge_gap_accuracy": 1.0,
        }
        self.router = MultimodalRouter()
        self.verifier = CrossModalVerifier()
        self.gaps = MultimodalGapDetector()

    def run(self, dataset: dict[str, Any]) -> MultimodalEvalSummary:
        cases=[]; totals={k:[] for k in self.thresholds}
        for raw in dataset["cases"]:
            case=self._case(raw); cases.append(case)
            for k,v in case.metrics.items(): totals[k].append(v)
        metrics={k:round(sum(v)/len(v),6) if v else 0.0 for k,v in totals.items()}
        reasons=[f"{k}={metrics[k]:.6f} < {t:.6f}" for k,t in self.thresholds.items() if metrics[k] < t]
        failed=[c.case_id for c in cases if not c.passed]
        if failed: reasons.append("case failures: "+", ".join(failed))
        return MultimodalEvalSummary(str(dataset["dataset_version"]), "block" if reasons else "pass", metrics, tuple(cases), tuple(reasons))

    def _case(self, raw: dict[str, Any]) -> MultimodalEvalCase:
        requested=tuple(EvidenceModality(x) for x in raw.get("requested_modalities",[]))
        required=tuple(EvidenceModality(x) for x in raw.get("required_modalities",[]))
        route=self.router.plan(str(raw["query"]),requested_modalities=requested,required_modalities=required)
        expected={EvidenceModality(x) for x in raw.get("expected_modalities",[])}
        metrics={}
        metrics["routing_accuracy"] = 1.0 if expected.issubset(set(route.modalities)) else 0.0
        metrics["required_modality_safety"] = 1.0 if set(route.required_modalities).issubset(set(route.modalities)) else 0.0

        candidates=[]
        citation_valid=True
        for idx,item in enumerate(raw.get("items",[])):
            modality=EvidenceModality(item["modality"])
            citation=MultimodalCitation(
                modality=modality, evidence_id=item.get("evidence_id"), page_number=item.get("page_number"),
                bbox=tuple(item["bbox"]) if item.get("bbox") else None, start_ms=item.get("start_ms"), end_ms=item.get("end_ms"),
                frame_index=item.get("frame_index"), frame_sha256=item.get("frame_sha256"), fhir_snapshot_id=item.get("fhir_snapshot_id"),
                fhir_resource_type=item.get("fhir_resource_type"), fhir_logical_id=item.get("fhir_logical_id"), fhir_version_id=item.get("fhir_version_id"),
                source_locator=item.get("source_locator",{}),
            )
            citation_valid = citation_valid and citation.validate()[0]
            candidates.append(MultimodalCandidate(
                item_id=f"eval-{idx}", modality=modality, domain=RAGDomain(item.get("domain","evidence")), source_id=f"src-{idx}", source_version="v1",
                text=item.get("text",""), score=0.9, confidence=0.9, authority_rank=90, citation=citation, metadata={}, retrieval_sources=("eval",),
            ))
        metrics["citation_anchor_accuracy"] = 1.0 if citation_valid else 0.0
        inconsistencies=self.verifier.verify(candidates)
        expected_inconsistency=bool(raw.get("expect_material_inconsistency",False))
        actual_inconsistency=any(i.severity == InconsistencySeverity.MATERIAL for i in inconsistencies)
        metrics["inconsistency_detection"] = 1.0 if expected_inconsistency == actual_inconsistency else 0.0
        gaps,_,_,_=self.gaps.detect(route=route,items=candidates,inconsistencies=inconsistencies)
        expected_gap=bool(raw.get("expect_blocking_gap",False))
        actual_gap=any(g.blocking for g in gaps)
        metrics["knowledge_gap_accuracy"] = 1.0 if expected_gap == actual_gap else 0.0
        reasons=[k for k,v in metrics.items() if v < self.thresholds[k]]
        return MultimodalEvalCase(str(raw["case_id"]), not reasons, metrics, tuple(reasons))
