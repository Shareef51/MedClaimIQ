from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Iterable


class KnowledgeSourceStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    RETIRED = "retired"


class KnowledgeVersionStatus(StrEnum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    ACTIVE = "active"
    RETIRED = "retired"
    REJECTED = "rejected"


class KnowledgeReleaseStatus(StrEnum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    PROMOTED = "promoted"
    REJECTED = "rejected"
    ROLLED_BACK = "rolled_back"


class ReindexAction(StrEnum):
    INCREMENTAL = "incremental"
    FULL = "full"
    DELETE = "delete"
    MIGRATE = "migrate"


class ReindexStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    RETRY = "retry"
    DEAD_LETTER = "dead_letter"


class DriftSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass(frozen=True)
class ProjectionTarget:
    embedding_model: str
    embedding_dimensions: int
    index_version: str

    def fingerprint(self) -> str:
        return sha256_json({
            "embedding_model": self.embedding_model,
            "embedding_dimensions": self.embedding_dimensions,
            "index_version": self.index_version,
        })


@dataclass(frozen=True)
class QualityAssessment:
    score: float
    passed: bool
    checks: dict[str, bool]
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class RetrievalDriftAssessment:
    severity: DriftSeverity
    blocking: bool
    recall_delta: float
    precision_delta: float
    ndcg_delta: float
    no_evidence_delta: float
    reasons: tuple[str, ...]


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def is_temporally_valid(*, valid_from: datetime | None, valid_to: datetime | None, at: datetime | None = None) -> bool:
    now = at or datetime.now(UTC)
    if valid_from is not None and now < valid_from:
        return False
    if valid_to is not None and now >= valid_to:
        return False
    return True


def assess_knowledge_quality(
    *,
    owner_present: bool,
    authority_rank: int,
    content_sha256: str,
    metadata: dict[str, Any],
    citation_coverage: float,
    valid_from: datetime | None,
    valid_to: datetime | None,
    required_metadata: Iterable[str] = ("title", "source_type"),
    minimum_authority_rank: int = 40,
    minimum_citation_coverage: float = 0.90,
) -> QualityAssessment:
    required = tuple(required_metadata)
    checks = {
        "owner_present": bool(owner_present),
        "authority_rank": authority_rank >= minimum_authority_rank,
        "content_hash": len(content_sha256) == 64 and all(ch in "0123456789abcdef" for ch in content_sha256.lower()),
        "metadata_complete": all(bool(metadata.get(key)) for key in required),
        "citation_coverage": 0 <= citation_coverage <= 1 and citation_coverage >= minimum_citation_coverage,
        "temporal_range": valid_to is None or valid_from is None or valid_to > valid_from,
    }
    weights = {
        "owner_present": 0.15,
        "authority_rank": 0.20,
        "content_hash": 0.15,
        "metadata_complete": 0.20,
        "citation_coverage": 0.20,
        "temporal_range": 0.10,
    }
    score = round(sum(weights[key] for key, ok in checks.items() if ok), 4)
    reasons = tuple(key for key, ok in checks.items() if not ok)
    return QualityAssessment(score=score, passed=not reasons, checks=checks, reasons=reasons)


def assess_retrieval_drift(
    *,
    baseline_recall: float,
    observed_recall: float,
    baseline_precision: float,
    observed_precision: float,
    baseline_ndcg: float,
    observed_ndcg: float,
    baseline_no_evidence_rate: float,
    observed_no_evidence_rate: float,
    max_recall_regression: float = 0.03,
    max_precision_regression: float = 0.05,
    max_ndcg_regression: float = 0.05,
    max_no_evidence_increase: float = 0.03,
) -> RetrievalDriftAssessment:
    recall_delta = round(observed_recall - baseline_recall, 6)
    precision_delta = round(observed_precision - baseline_precision, 6)
    ndcg_delta = round(observed_ndcg - baseline_ndcg, 6)
    no_evidence_delta = round(observed_no_evidence_rate - baseline_no_evidence_rate, 6)
    reasons: list[str] = []
    if recall_delta < -max_recall_regression:
        reasons.append("recall_regression")
    if precision_delta < -max_precision_regression:
        reasons.append("precision_regression")
    if ndcg_delta < -max_ndcg_regression:
        reasons.append("ndcg_regression")
    if no_evidence_delta > max_no_evidence_increase:
        reasons.append("no_evidence_rate_increase")
    critical = "recall_regression" in reasons or len(reasons) >= 2
    severity = DriftSeverity.CRITICAL if critical else DriftSeverity.WARNING if reasons else DriftSeverity.INFO
    return RetrievalDriftAssessment(
        severity=severity,
        blocking=bool(reasons),
        recall_delta=recall_delta,
        precision_delta=precision_delta,
        ndcg_delta=ndcg_delta,
        no_evidence_delta=no_evidence_delta,
        reasons=tuple(reasons),
    )
