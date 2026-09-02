# Multimodal Reviewer Investigation Workbench

The reviewer workbench projects governed multimodal evidence into a human-operable investigation surface. It does not create a new evidence authority and it does not grant AI agents or UI components authority to finalize claims.

## Evidence visualization

The workbench can inspect accepted claim evidence using exact multimodal citation anchors:

- PDF/document citations: page plus bounding box. PDF pages are rendered server-side with the cited rectangle highlighted.
- Images: read-only source preview plus bounding-box overlay.
- Tables/invoices: citation anchor plus structured extraction data.
- Audio: transcript/extracted text plus start/end timecodes and a player jump control.
- Video: transcript/keyframe provenance plus timecode, frame index, frame SHA-256 and player jump control.
- FHIR: exact snapshot, resource type, logical ID and version with canonical resource comparison.

Raw object-store keys are not returned to browser code. Media bytes are streamed through the authenticated same-origin reviewer BFF; the BFF obtains a short-lived signed source URL server-side and forwards HTTP Range requests for audio/video seeking.

## Cross-modal investigations

The backend joins the latest multimodal evidence pack, evidence items, cross-modal inconsistencies, LangGraph multimodal investigations, multimodal agent findings and the durable human checkpoint. Findings cite exact `mm:*` evidence keys and the UI can drill from a finding to the corresponding source/citation.

Missing required modalities and material conflicts remain deterministic human-review conditions created by the orchestration layer. The UI displays these conditions; it cannot clear them by hiding a panel.

## Reviewer annotations

An authorized claims reviewer with an active review lease may create immutable annotations against:

- a multimodal evidence item;
- a cross-modal inconsistency;
- an agent finding;
- a human checkpoint; or
- an evidence artifact.

Each annotation stores its exact target, citation/anchor metadata, SHA-256 of the body, reviewer identity, idempotency key and trace ID. Annotation creation also emits a real-time `review.multimodal.annotation.added` event.

## Human decision boundary

All evidence visualization and AI findings remain advisory inputs to the pre-existing reviewer decision panel. Final approve/deny/partial/escalate operations still require the exclusive reviewer lease, current claim status version, evidence snapshot, structured reason code, human rationale, and an override reason when human judgment differs from AI decision support.
