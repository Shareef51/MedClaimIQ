# Multimodal RAG and Cross-Modal Evidence Verification

MedClaimIQ's multimodal retrieval layer combines already-authorized textual RAG evidence with citation-addressable document extraction units and versioned FHIR snapshots. It does not create a parallel authorization model and it does not turn derived visual/audio descriptions into authoritative medical facts.

## Retrieval path

1. Require claim read access plus the internal `claim:view_ai_findings` permission.
2. Build the existing tenant/claim/patient/ACL retrieval scope.
3. Route only the modalities needed for the question: text/document, table, image, audio, video, and/or FHIR.
4. Use Advanced Agentic RAG for governed textual knowledge. This preserves the Release 30 PostgreSQL knowledge-release eligibility check.
5. Read only successful claim extraction units for OCR/layout/table/audio/video evidence.
6. Read claim-scoped, versioned FHIR snapshots from PostgreSQL.
7. Normalize every result into a modality-tagged candidate with a source/version and exact citation anchor.
8. Apply modality-aware reranking and source/modality diversification.
9. Compare cross-modal amounts, codes, and dates deterministically and preserve material mismatches instead of resolving them silently.
10. Calculate modality coverage, citation coverage, evidence confidence, and explicit knowledge gaps.
11. Persist an immutable evidence-pack projection that contains hashes, scores, anchors and source/version identifiers rather than raw media bytes.
12. Return `answerable`, `partial`, or `insufficient`. Material cross-modal inconsistency is not autonomously adjudicated; it requires human review.

## Citation contract

- PDF/document/table: evidence ID plus page and, when available, bounding box/table locator.
- Image: evidence ID plus image/OCR locator and optional bounding box/image SHA-256.
- Audio: evidence ID plus start/end milliseconds.
- Video transcript: evidence ID plus timecode.
- Video keyframe: evidence ID, timecode, frame index and frame SHA-256.
- FHIR: immutable snapshot ID plus resource type, logical ID and `meta.versionId` equivalent.

The citation points back to governed/accepted source material. Model-generated captions or visual descriptions are never treated as citations themselves.

## Visual descriptors

Image OCR always creates an image-level derived unit containing OCR/layout metadata. An approved `VisualDescriptorProvider` can additionally enrich images or sampled video keyframes with a bounded description/label set. Such descriptors are derived evidence metadata, may improve retrieval, and remain subject to provenance, grounding and human-review controls. They do not override original image/video evidence.

## Cross-modal inconsistency policy

The deterministic verifier currently detects disagreements in monetary amounts, medical/billing codes, and service-date-like values across different modalities. Amount/code conflicts are classified as material and force an insufficient-evidence/human-review outcome. The system records hashes of conflicting values in persistent telemetry rather than duplicating those values into operational history.

## Knowledge governance

Governed textual knowledge is still resolved through Advanced RAG, so retired, expired, future-dated or unapproved knowledge remains ineligible even if it is highly similar to an image/transcript query. Claim evidence extraction units and FHIR snapshots use their existing acceptance/version authority models.

## Privacy and telemetry

`multimodal_rag_items` stores content SHA-256, citation anchors, source/version, modality, rank and scores. It does not store raw image/video/audio bytes. Raw media stays in accepted object storage and authorized evidence tables.

## Evaluation

Run:

```bash
python scripts/run_multimodal_rag_evaluations.py --gate
```

The deterministic suite measures modality routing, required-modality safety, citation-anchor correctness, material inconsistency detection and knowledge-gap behavior. Reports are written to `artifacts/multimodal-rag/` and the release pipeline requires the `multimodal-rag-quality` gate.
