# ADR — Governed multimodal retrieval over accepted evidence

## Decision

Extend the existing RAG/evidence architecture with a modality-aware fusion layer rather than introducing an independent multimodal datastore as a new source of truth. Textual governed knowledge continues through Advanced RAG; OCR/layout/table/audio/video extraction units come from successful document-intelligence runs; FHIR candidates come from immutable versioned snapshots. Raw media remains in accepted object storage.

## Why

This preserves tenant/claim/ACL authorization, source-version provenance, Release 30 knowledge-release authority and the human-final-decision boundary. It also allows image/audio/video evidence to be searched and cross-checked without copying sensitive media into telemetry systems.

## Consequences

Multimodal evidence packs contain source references, hashes, citations and confidence rather than raw media. Optional vision-model descriptors are derived evidence only. Material cross-modal contradictions route to human review. Qdrant remains a rebuildable textual retrieval projection rather than the authority for media validity.

## Rejected

A separate vision-vector service that can return media without the existing claim/tenant authorization and evidence lifecycle checks, because it would duplicate policy enforcement and create a second uncontrolled evidence authority.
