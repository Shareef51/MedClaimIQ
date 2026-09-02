# Multimodal Agent Orchestration

MedClaimIQ binds Release 32 multimodal evidence packs into the durable LangGraph specialist workflow without giving agents unrestricted retrieval or claim-mutation capabilities.

## Specialist profiles

Hospital Verification, Invoice Verification, and Fraud/Waste execute as parallel LangGraph branches. Evidence Fusion, Critic, and Decision Support execute after fan-in and receive prior specialist findings plus a bounded multimodal pack of their own.

Every agent profile defines an allowlist of modalities, domains, required modalities, and a maximum pack size. A caller or model can narrow this scope but cannot widen it.

## Citation provenance

Multimodal items are exposed to the model with `mm:<item_id>` evidence keys and exact Release 32 citation anchors. Findings may reference only evidence keys actually supplied in the immutable request context. Citation maps are copied into finding metadata for reviewer/audit reconstruction.

## Deterministic escalation

Material cross-modal conflicts, missing required modalities, or an insufficient multimodal evidence pack create deterministic review-required findings. The human gate reads persisted multimodal investigations and emits a durable LangGraph checkpoint using `multimodal_conflict` or `missing_required_modality` when applicable.

Agents cannot suppress these escalations, approve/deny a claim, mutate evidence, change tenant/claim scope, or bypass Release 30 governed-knowledge eligibility.
