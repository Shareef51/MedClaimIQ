# ADR — Multimodal specialist orchestration

## Decision
Use profile-bounded multimodal retrieval as a read-only pre-step for selected specialist agents. Preserve Release 32 packs and citations, persist one immutable investigation record per workflow/agent/attempt, and use deterministic human-escalation rules outside the model.

## Rationale
Parallel specialists need modality-specific evidence but must not receive database/vector-store authority. The retrieval service already enforces tenant/claim/ACL and knowledge lifecycle boundaries. Persisting investigation provenance makes cross-modal agent reasoning auditable while keeping raw media outside orchestration telemetry.

## Consequences
Material conflicts and missing required modalities can never be silently resolved by the model. Final claim decisions remain human-only.
