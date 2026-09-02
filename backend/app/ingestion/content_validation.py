from __future__ import annotations

import re
import struct
from dataclasses import dataclass
from pathlib import PurePath

from app.domain.ingestion import ALLOWED_UPLOAD_TYPES, MediaKind


class ContentValidationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class DetectedContent:
    media_type: str
    media_kind: MediaKind
    metadata: dict[str, object]


def safe_extension(filename: str) -> str:
    # Only the extension is persisted. User-controlled basenames may contain PHI,
    # path separators, control characters, or misleading double extensions.
    leaf = PurePath(filename.replace("\\", "/")).name
    suffix = PurePath(leaf).suffix.lower()
    if suffix not in ALLOWED_UPLOAD_TYPES:
        raise ContentValidationError("unsupported_extension", "file extension is not allowed")
    return suffix


def validate_declared_upload(*, extension: str, media_type: str, byte_size: int, max_bytes: int) -> MediaKind:
    expected_media_type, kind = ALLOWED_UPLOAD_TYPES[extension]
    normalized = media_type.split(";", 1)[0].strip().lower()
    if normalized != expected_media_type:
        raise ContentValidationError(
            "declared_type_mismatch", "declared media type does not match the file extension"
        )
    if byte_size <= 0:
        raise ContentValidationError("empty_upload", "upload must contain at least one byte")
    if byte_size > max_bytes:
        raise ContentValidationError("upload_too_large", "upload exceeds the configured size limit")
    return kind


def detect_content(sample: bytes, *, extension: str) -> DetectedContent:
    if sample.startswith(b"%PDF-"):
        return DetectedContent("application/pdf", MediaKind.PDF, _pdf_metadata(sample))
    if sample.startswith(b"\x89PNG\r\n\x1a\n"):
        return DetectedContent("image/png", MediaKind.IMAGE, _png_metadata(sample))
    if sample.startswith(b"\xff\xd8\xff"):
        return DetectedContent("image/jpeg", MediaKind.IMAGE, _jpeg_metadata(sample))
    if sample.startswith((b"II*\x00", b"MM\x00*")):
        return DetectedContent("image/tiff", MediaKind.IMAGE, {"format": "tiff"})
    if sample.startswith(b"RIFF") and sample[8:12] == b"WAVE":
        return DetectedContent("audio/wav", MediaKind.AUDIO, _wav_metadata(sample))
    if sample.startswith(b"ID3") or (len(sample) >= 2 and sample[0] == 0xFF and sample[1] & 0xE0 == 0xE0):
        return DetectedContent("audio/mpeg", MediaKind.AUDIO, {"format": "mp3", "probe_status": "basic"})
    if len(sample) >= 12 and sample[4:8] == b"ftyp":
        major_brand = sample[8:12].decode("ascii", "replace")
        media_type = "video/quicktime" if major_brand == "qt  " else "video/mp4"
        return DetectedContent(
            media_type,
            MediaKind.VIDEO,
            {"container": "iso-bmff", "major_brand": major_brand.strip(), "probe_status": "basic"},
        )
    if sample.startswith(b"\x1aE\xdf\xa3"):
        return DetectedContent("video/webm", MediaKind.VIDEO, {"container": "webm", "probe_status": "basic"})

    stripped = sample.lstrip()
    if extension == ".json" and stripped.startswith((b"{", b"[")):
        try:
            sample.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ContentValidationError("invalid_json_encoding", "JSON evidence must be UTF-8") from exc
        return DetectedContent(
            "application/json", MediaKind.JSON, {"encoding": "utf-8", "probe_status": "prefix-validated"}
        )
    if extension == ".csv" and b"\x00" not in sample:
        try:
            text = sample.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ContentValidationError("invalid_csv_encoding", "CSV evidence must be UTF-8") from exc
        first_line = text.splitlines()[0] if text.splitlines() else ""
        if "," in first_line or ";" in first_line or "\t" in first_line:
            return DetectedContent("text/csv", MediaKind.CSV, {"encoding": "utf-8"})

    raise ContentValidationError("unknown_content_type", "object bytes do not match an allowed media type")


def enforce_detected_matches_declared(
    *, detected: DetectedContent, declared_media_type: str, expected_kind: MediaKind
) -> None:
    declared = declared_media_type.split(";", 1)[0].strip().lower()
    if detected.media_type != declared or detected.media_kind is not expected_kind:
        raise ContentValidationError(
            "content_type_spoofing",
            "server-detected content does not match the declared upload type",
        )


def _pdf_metadata(sample: bytes) -> dict[str, object]:
    # Accurate page counting belongs to the isolated document-intelligence worker.
    # This probe records only conservative ingestion metadata.
    version_match = re.match(br"%PDF-(\d\.\d)", sample[:16])
    version = version_match.group(1).decode("ascii") if version_match else None
    return {"format": "pdf", "pdf_version": version, "probe_status": "basic"}


def _png_metadata(sample: bytes) -> dict[str, object]:
    if len(sample) >= 24:
        width, height = struct.unpack(">II", sample[16:24])
        return {"format": "png", "width": width, "height": height, "probe_status": "basic"}
    return {"format": "png", "probe_status": "partial"}


def _jpeg_metadata(sample: bytes) -> dict[str, object]:
    offset = 2
    while offset + 9 < len(sample):
        if sample[offset] != 0xFF:
            offset += 1
            continue
        marker = sample[offset + 1]
        offset += 2
        if marker in {0xD8, 0xD9}:
            continue
        if offset + 2 > len(sample):
            break
        length = int.from_bytes(sample[offset : offset + 2], "big")
        if length < 2 or offset + length > len(sample):
            break
        if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}:
            height = int.from_bytes(sample[offset + 3 : offset + 5], "big")
            width = int.from_bytes(sample[offset + 5 : offset + 7], "big")
            return {"format": "jpeg", "width": width, "height": height, "probe_status": "basic"}
        offset += length
    return {"format": "jpeg", "probe_status": "partial"}


def _wav_metadata(sample: bytes) -> dict[str, object]:
    metadata: dict[str, object] = {"format": "wav", "probe_status": "basic"}
    if len(sample) >= 28 and sample[12:16] == b"fmt ":
        metadata["channels"] = int.from_bytes(sample[22:24], "little")
        metadata["sample_rate_hz"] = int.from_bytes(sample[24:28], "little")
    return metadata
