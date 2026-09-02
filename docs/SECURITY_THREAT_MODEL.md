# MedClaimIQ security threat model

## Crown jewels
Electronic protected health information, claim/evidence records, OIDC sessions, authorization grants, evidence lineage, human decisions, audit history, model/tool execution metadata, cryptographic keys, and production secrets.

## Trust boundaries
Browser ↔ Next.js BFF; BFF ↔ FastAPI; FastAPI ↔ PostgreSQL/Redis/Qdrant/object storage; workers ↔ Redpanda; MedClaimIQ ↔ FHIR/identity/model/tool providers; application ↔ observability exporters.

## High-priority threats and controls
- **Cross-tenant disclosure:** server-side tenant resolution, RBAC/ABAC, RLS, claim/relationship checks, filtered RAG.
- **Prompt/tool injection:** untrusted-evidence boundary, injection screening, schema outputs, MCP allowlists, approval gates.
- **Malicious uploads:** quarantine, magic/MIME checks, malware scan, immutable source fingerprinting.
- **Credential theft:** OIDC/PKCE, HttpOnly encrypted BFF cookies, no browser token storage, secret manager/KMS production boundary.
- **PHI leakage through logs/telemetry:** centralized classification/DLP, hashed prompt/query fields, optional exporters disabled by default.
- **Supply-chain compromise:** lock/pin strategy, SBOM, SAST, secret scan, dependency/image/IaC scanning, signed image digest and provenance.
- **Audit tampering:** append-only tables plus hash-chain/HMAC export manifests.
- **Concurrent/stale human decisions:** review leases, optimistic status version, immutable decision evidence snapshots.
- **Destructive retention mistakes:** disposition requests are dry-run/approval-first; no generic autonomous delete tool.
- **DoS/resource abuse:** request rate limits, file limits, worker backpressure, circuit breakers, bounded graph/query/agent execution.

## Explicit non-goals
This repository does not implement physical facility controls, workforce screening/training, legal contracting, or certify HIPAA compliance.
