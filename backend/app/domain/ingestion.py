from __future__ import annotations

from enum import StrEnum
from typing import Final


class UploadSessionStatus(StrEnum):
    INITIATED = "initiated"
    UPLOADED = "uploaded"
    VERIFYING = "verifying"
    QUARANTINED = "quarantined"
    ACCEPTED = "accepted"
    DUPLICATE = "duplicate"
    REJECTED = "rejected"
    EXPIRED = "expired"
    ABORTED = "aborted"


class MalwareVerdict(StrEnum):
    CLEAN = "clean"
    INFECTED = "infected"
    SUSPICIOUS = "suspicious"
    ERROR = "error"


class MediaKind(StrEnum):
    PDF = "pdf"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    JSON = "json"
    CSV = "csv"


class IngestionEventType(StrEnum):
    UPLOAD_INITIATED = "evidence.upload.initiated"
    UPLOAD_COMPLETED = "evidence.upload.completed"
    VERIFICATION_STARTED = "evidence.verification.started"
    CONTENT_VERIFIED = "evidence.content.verified"
    MALWARE_SCAN_COMPLETED = "evidence.malware_scan.completed"
    MALWARE_SCAN_FAILED = "evidence.malware_scan.failed"
    INGESTION_ACCEPTED = "evidence.ingestion.accepted"
    INGESTION_DUPLICATE = "evidence.ingestion.duplicate"
    INGESTION_REJECTED = "evidence.ingestion.rejected"
    PROCESSING_REQUESTED = "evidence.processing.requested"


class OutboxStatus(StrEnum):
    PENDING = "pending"
    CLAIMED = "claimed"
    PUBLISHED = "published"
    FAILED = "failed"


# Initiation validates both extension and declared MIME. The worker later treats both
# as untrusted hints and validates the actual bytes before any artifact is accepted.
ALLOWED_UPLOAD_TYPES: Final[dict[str, tuple[str, MediaKind]]] = {
    ".pdf": ("application/pdf", MediaKind.PDF),
    ".png": ("image/png", MediaKind.IMAGE),
    ".jpg": ("image/jpeg", MediaKind.IMAGE),
    ".jpeg": ("image/jpeg", MediaKind.IMAGE),
    ".tif": ("image/tiff", MediaKind.IMAGE),
    ".tiff": ("image/tiff", MediaKind.IMAGE),
    ".wav": ("audio/wav", MediaKind.AUDIO),
    ".mp3": ("audio/mpeg", MediaKind.AUDIO),
    ".mp4": ("video/mp4", MediaKind.VIDEO),
    ".mov": ("video/quicktime", MediaKind.VIDEO),
    ".webm": ("video/webm", MediaKind.VIDEO),
    ".json": ("application/json", MediaKind.JSON),
    ".csv": ("text/csv", MediaKind.CSV),
}


DEFAULT_MAX_BYTES_BY_KIND: Final[dict[MediaKind, int]] = {
    MediaKind.PDF: 50 * 1024 * 1024,
    MediaKind.IMAGE: 25 * 1024 * 1024,
    MediaKind.AUDIO: 150 * 1024 * 1024,
    MediaKind.VIDEO: 500 * 1024 * 1024,
    MediaKind.JSON: 25 * 1024 * 1024,
    MediaKind.CSV: 50 * 1024 * 1024,
}
