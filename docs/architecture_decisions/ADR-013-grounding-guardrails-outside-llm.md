# ADR-013: Enforce RAG grounding and prompt-injection controls outside the LLM

## Status

Accepted.

## Context

MedClaimIQ retrieves evidence from user uploads, OCR, FHIR systems, policies, invoices, transcripts, structured SQL, and relationship graphs. Some sources can be attacker-controlled or contain accidental instructions. Retrieval relevance alone does not establish trust, factual support, authorization, or safe model behavior.

## Decision

Grounding and critical safety controls are implemented as deterministic application services outside the language model.

The application will:

1. treat every retrieved evidence payload as untrusted data;
2. screen retrieved content before it enters model context;
3. exclude suspicious evidence from the generation context while preserving its immutable audit record;
4. calculate evidence quality and answerability before generation;
5. require evidence-key citations for material generated statements;
6. verify citation identity/version/locator against the evidence pack;
7. reject partially grounded, unsupported, numerically inconsistent, code-inconsistent, or contradiction-suppressing statements;
8. allow only bounded, authorization-preserving retrieval repair;
9. route unresolved material contradictions, injection findings, or persistent evidence insufficiency to human review;
10. keep final claim decisions under human authority.

## Consequences

This architecture adds latency and deterministic validation work, but improves replayability, security, evaluation, and reviewer trust. It also keeps future model/provider changes from weakening authorization or evidence rules.

No single prompt-injection detector is assumed to be complete. The scanner is a first-line signal combined with least privilege, typed tool boundaries, claim-scoped retrieval, immutable provenance, output validation, and human escalation.
