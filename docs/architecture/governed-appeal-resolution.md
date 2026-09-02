# Release 39 — Evidence-Bound Appeal Resolution, Dual Control & Governed Final Closure

## Purpose
Release 39 converts Release 38 recommendation-only reconsideration into a human-only controlling appeal decision. The original adjudication and original evidence snapshot are never mutated. A new appeal decision packet binds the locked reconsideration snapshot, citation set, resolved material contradictions, human rationale, amount reconciliation, and the latest recommendation-only run.

## Control flow
1. Independent human reviewer prepares an appeal decision packet.
2. Completeness validation blocks stale/unlocked snapshots, invalid or missing citations, open missing-evidence requests, unresolved material contradictions, and undocumented recommendation disagreement.
3. The packet is hash locked. Overturns and material amount changes enter dual control.
4. A second independent human reviewer must approve when dual control is required. The reviewer cannot be the primary appeal reviewer or an original adjudication reviewer.
5. The primary independent human reviewer closes the locked packet with optimistic appeal/packet version checks.
6. Closure appends an immutable `appeal_final_resolution` decision-history version, closes durable reconsideration checkpoints and appeal SLA tasks, and creates a draft reconsideration notice.
7. A separate authorized human releases the notice. Release 37 transport can then queue/retry/reconcile delivery without gaining adjudication authority.

## Financial reconciliation
The service deterministically derives the original approved amount from the original locked human decision and compares it with the proposed reconsidered amount. A change is material when it meets the configured absolute or percentage threshold. Overturns are always dual-control.

## Provenance
The final resolution binds original decision ID, original packet ID, appeal ID, Release 38 snapshot ID/hash, recommendation run, citation references, material-comparison resolutions, annotations, checkpoints, primary reviewer, second reviewer when required, packet lock hash, final resolution hash, superseding decision-history hash, notice ID, and transport/audit records.

## Authority boundary
LLM, LangGraph, RAG, MCP, background automation, notification workers, and transport providers have zero authority to affirm, modify, overturn, approve, deny, or financially adjudicate. Only active authorized human claims reviewers can create the controlling appeal outcome; dual-control cases require two independent humans.
