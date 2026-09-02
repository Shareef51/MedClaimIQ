# ADR-006: Quarantine-first evidence ingestion

## Status

Accepted.

## Decision

All user/provider evidence uploads enter an S3-compatible quarantine prefix through a pre-signed POST. Upload completion does not create an evidence artifact. A worker must independently verify object ownership metadata, VersionId/ETag, size, SHA-256, byte signature/MIME, and malware verdict. Only a clean, unique object may be promoted to the accepted prefix and registered as an `EvidenceArtifact`.

Raw client filenames are never used as object keys and are not persisted. Domain processing events are append-only and are paired transactionally with outbox rows for eventual event-bus delivery.

## Why

Directly parsing a freshly uploaded object gives malicious, oversized, spoofed, overwritten, or infected content a path into OCR, RAG, model prompts, and analyst workflows. Quarantine-first ingestion converts file acceptance into an explicit security decision with a persistent audit trail.

## Consequences

Uploads become asynchronous after completion, scanners and object storage must be highly available, and production S3-compatible buckets should use versioning. This additional complexity is intentional because medical-claims evidence is an untrusted external input boundary.
