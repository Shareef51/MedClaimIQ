# Secure Multimodal Evidence Ingestion

MedClaimIQ treats every uploaded object as hostile until it has passed server-side verification and malware scanning. A signed upload is permission to place bytes into a quarantine location; it is not evidence acceptance.

## Upload flow

```text
Authenticated user
      |
      v
claim-scoped EVIDENCE_UPLOAD authorization
      |
      v
idempotent upload session
      |
      v
pre-signed S3/MinIO POST
(exact content-length policy + signed tenant/claim/session metadata)
      |
      v
quarantine/<tenant>/<claim>/<session>/object.ext
      |
      v
completion API confirms object identity
      |
      v
append-only completion event + transactional outbox
      |
      v
quarantine worker
  - re-check VersionId/ETag
  - stream byte count
  - server SHA-256
  - magic-byte/MIME detection
  - declared/detected anti-spoofing check
  - ClamAV streaming scan
  - duplicate lookup
      |
      +---- infected/suspicious ---> rejected; remains quarantined
      |
      +---- duplicate -------------> existing evidence reference; duplicate object removed
      |
      v
accepted/<tenant>/<claim>/<session>/<hash-prefix>.ext
      |
      v
EvidenceArtifact(status=accepted)
      |
      v
evidence.processing.requested
```

## Security invariants

- Client filenames never become storage keys and are not persisted in raw form. Only the extension and SHA-256 of the submitted filename are stored.
- The object key is server-generated and opaque to the original filename.
- S3/MinIO upload metadata binds the object to the upload session, tenant, and claim.
- A presigned POST uses an exact content-length condition. The completion endpoint and worker independently verify byte size again.
- ETag/VersionId are recorded at completion and revalidated before and after scanning. Production buckets should keep versioning enabled; object lock/retention can be added where required.
- Client-provided MIME type, extension, SHA-256, and metadata are hints only. The server computes its own SHA-256 and detects media type from bytes.
- Malware scanning is fail-closed by default. A scanner error leaves the object quarantined for retry.
- OCR, document parsing, transcription, RAG indexing, agents, and LLMs are prohibited from reading quarantine objects.
- Processing-domain events are append-only. Delivery state lives separately in a mutable transactional outbox.
- Event payloads contain internal IDs and operational metadata only; document content and raw filenames are excluded.

## Supported ingestion types

The secure boundary currently accepts PDF, PNG, JPEG, TIFF, WAV, MP3, MP4, MOV, WebM, JSON, and UTF-8 CSV. Rich document parsing, OCR, audio transcription, and video analysis are downstream processing responsibilities after acceptance.

## Media metadata

The ingestion probe intentionally collects only low-risk, bounded metadata. It extracts basic PDF version data, PNG/JPEG dimensions where available, WAV channels/sample rate, and basic MP4/WebM/MP3 container information. Accurate PDF page layout, audio duration, video keyframes, and clinical document semantics belong to isolated downstream workers.

## Real-time event boundary

Each domain event creates a same-transaction outbox row on topic `medclaimiq.evidence.events.v1`, partitioned by `claim_id`. A later event-bus layer can publish these rows to Kafka/Redpanda without changing the ingestion transaction model.
