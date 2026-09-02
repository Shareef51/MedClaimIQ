from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class ExtractionRunStatus(StrEnum):
    REQUESTED = "requested"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    RETRY_PENDING = "retry_pending"
    DEAD_LETTERED = "dead_lettered"
    FAILED = "failed"


class ExtractionUnitType(StrEnum):
    TEXT = "text"
    TABLE = "table"
    IMAGE = "image"
    AUDIO_SEGMENT = "audio_segment"
    VIDEO_KEYFRAME = "video_keyframe"
    METADATA = "metadata"


class ExtractionEventType(StrEnum):
    REQUESTED = "document.extraction.requested"
    STARTED = "document.extraction.started"
    UNIT_EXTRACTED = "document.extraction.unit_extracted"
    SUCCEEDED = "document.extraction.succeeded"
    RETRY_SCHEDULED = "document.extraction.retry_scheduled"
    DEAD_LETTERED = "document.extraction.dead_lettered"
    FAILED = "document.extraction.failed"


@dataclass(frozen=True)
class CitationAnchor:
    evidence_id: str
    page_number: int | None = None
    start_ms: int | None = None
    end_ms: int | None = None
    bbox: tuple[float, float, float, float] | None = None
    frame_index: int | None = None
    frame_sha256: str | None = None
    source_locator: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.page_number is not None and self.page_number < 1:
            raise ValueError("page_number must be >= 1")
        if (self.start_ms is None) != (self.end_ms is None):
            raise ValueError("start_ms and end_ms must be provided together")
        if self.start_ms is not None and (self.start_ms < 0 or self.end_ms < self.start_ms):
            raise ValueError("timestamp range is invalid")
        if self.frame_index is not None and self.frame_index < 0:
            raise ValueError("frame_index must be non-negative")
        if self.frame_sha256 is not None and len(self.frame_sha256) != 64:
            raise ValueError("frame_sha256 must be a SHA-256 hex digest")


@dataclass(frozen=True)
class ExtractionUnit:
    unit_type: ExtractionUnitType
    sequence: int
    text: str | None
    structured_data: dict[str, object]
    confidence: float
    citation: CitationAnchor

    def __post_init__(self) -> None:
        if self.sequence < 0:
            raise ValueError("sequence must be non-negative")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        if not self.text and not self.structured_data:
            raise ValueError("an extraction unit must carry text or structured data")


@dataclass(frozen=True)
class ExtractionBundle:
    parser_name: str
    parser_version: str
    media_type: str
    units: tuple[ExtractionUnit, ...]
    warnings: tuple[str, ...] = ()
    metadata: dict[str, object] = field(default_factory=dict)

    @property
    def aggregate_confidence(self) -> float:
        if not self.units:
            return 0.0
        # Conservative average: low-confidence units should remain visible in the aggregate.
        return round(sum(unit.confidence for unit in self.units) / len(self.units), 6)


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    base_delay_seconds: int = 15
    max_delay_seconds: int = 300

    def delay_seconds(self, attempt_number: int) -> int:
        if attempt_number < 1:
            raise ValueError("attempt_number must be >= 1")
        return min(self.base_delay_seconds * (2 ** (attempt_number - 1)), self.max_delay_seconds)

    def should_dead_letter(self, attempt_number: int) -> bool:
        return attempt_number >= self.max_attempts
