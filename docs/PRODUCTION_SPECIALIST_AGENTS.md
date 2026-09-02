# Production Specialist Agents

MedClaimIQ uses specialist agents only for bounded probabilistic reasoning. Authentication, authorization, tenant scope, claim lifecycle transitions, final reviewer decisions, evidence provenance, and authoritative graph mutations remain deterministic services.

## Agent set

The registry contains Intake, Hospital/FHIR Verification, Invoice Verification, Eligibility, Policy, Coding, Duplicate Claim, Fraud/Waste, Denial Risk, Evidence Fusion, Critic, Decision Support, and Human Review Router agents.

## Evidence-only contract

Every agent is bound to one immutable evidence-pack identifier. The evidence snapshot provider must return the same claim-scoped pack. Tools are read-only and limited to evidence listing, evidence lookup, local evidence search, and contradiction listing. No agent is given a database session, lifecycle mutator, unrestricted HTTP client, tenant switch, filesystem writer, or payment tool.

Every material finding must reference evidence keys present in the pack. Unknown keys are rejected. Retrieved text remains untrusted data and cannot override the system prompt.

## Structured model output

The OpenAI adapter uses the Responses API with strict JSON Schema. The schema intentionally has no final-decision or action-execution fields. Decision Support can emit an advisory recommendation category, but an approval/denial support recommendation automatically requires human review.

## Prompt versioning

Each specialist has a stable prompt key, semantic prompt version, SHA-256 prompt hash, model selection, allowed tool list, and confidence contract. Agent findings retain prompt key/version metadata so evaluation can reproduce the reasoning contract.

## Failure behavior

Transient provider/network errors are retryable within the orchestration ceiling. Schema/evidence/authorization contract violations are non-retryable. Missing or conflicting evidence produces insufficient-evidence or human-review output rather than fabricated certainty.
