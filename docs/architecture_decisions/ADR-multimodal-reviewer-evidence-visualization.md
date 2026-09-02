# ADR — Multimodal reviewer evidence visualization

## Decision

Use a server-composed, claim-authorized multimodal investigation view and same-origin media streaming rather than exposing object-store locations or embedding external signed URLs directly in the reviewer application.

PDF citation highlighting is rendered server-side from the accepted evidence object with PyMuPDF. Audio/video source bytes are range-streamed through the reviewer BFF. Reviewer annotations are append-only and require the existing exclusive review lease.

## Rationale

This preserves strict browser CSP, avoids leaking storage topology, provides exact citation drill-down, and reuses the existing tenant/claim authorization and human-final-decision controls.

## Consequences

The API image includes PyMuPDF for page rendering. The media BFF must preserve Range/Content-Range headers. Reviewer evidence is read-only; annotations are separate immutable audit objects rather than edits to the source evidence.
