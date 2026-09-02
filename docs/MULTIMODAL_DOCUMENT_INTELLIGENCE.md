# Multimodal Document Intelligence

MedClaimIQ processes only evidence that has already passed the quarantine and malware boundary. Heavy parsing is never performed in the request-serving API process.

## Pipeline

`accepted evidence -> isolated parser -> extraction run -> citation units -> normalized manifest -> derived evidence -> DERIVED_FROM lineage -> normalized event`

PDF extraction is layout-aware and records page numbers and bounding boxes when available. OCR units retain image/page coordinates. Audio transcript units retain start/end timestamps. The optional Faster-Whisper adapter provides local transcription. Video processing uses FFmpeg to extract 16 kHz mono audio plus deterministic keyframe samples, combines the transcript with keyframe hashes/timestamps, and keeps parser execution isolated. Tables are stored as structured extraction units rather than flattened prose.

## Provenance and citations

Every extraction unit points to the immutable accepted source evidence and stores a citation anchor. A normalized extraction manifest is written as a non-authoritative derived evidence artifact. Evidence lineage records the parser/transformation name and version. This is the provenance boundary later RAG indexing must preserve.

## Confidence

Per-unit confidence is retained. Low-confidence content is not silently deleted; it can be flagged for downstream review. Aggregate confidence is deliberately conservative and must never be interpreted as medical or claim-decision confidence.

## Parser isolation

Local development uses a subprocess with a wall-clock timeout. Production deployment should run document parsers in restricted worker containers/pods with no inbound service credentials, no network unless explicitly required, a read-only root filesystem, non-root UID, CPU/memory/ephemeral-storage limits, and seccomp/AppArmor controls.

## Reliability

Extraction attempts are idempotent per evidence/pipeline/attempt. Retryable infrastructure/parser failures use exponential backoff. Exhausted retryable work is persisted to an extraction dead-letter table with a replay payload. Extraction units and DLQ rows are append-only and tenant isolated with PostgreSQL RLS.
