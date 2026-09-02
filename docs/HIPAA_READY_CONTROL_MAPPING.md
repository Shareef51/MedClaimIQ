# HIPAA-ready technical control mapping

MedClaimIQ is a **HIPAA-ready architecture**, not a certification of compliance. The demo uses synthetic/de-identified data. An organization deploying PHI must complete legal, organizational, administrative, physical, contractual, workforce, and technical requirements outside this repository.

The technical baseline maps the currently effective HIPAA Security Rule to NIST SP 800-66 Rev. 2 and application controls. The January 2025 HHS Security Rule changes are a proposed rule and are tracked as future requirements rather than represented as currently effective law.

| Safeguard area | MedClaimIQ technical evidence |
|---|---|
| Risk analysis / risk management | Threat model, security readiness gate, AI quality gate, dependency/container/IaC scans |
| Access control | OIDC, server-resolved tenant membership, RBAC/ABAC, PostgreSQL forced RLS, relationship scoping |
| Audit controls | Append-only business/security histories, trace correlation, tamper-evident audit exports |
| Integrity | Evidence SHA-256, object version IDs, immutable evidence packs, hash-chain exports, signed build artifacts |
| Person/entity authentication | OIDC issuer/audience/signature validation and persisted subject mapping |
| Transmission security | HTTPS/TLS production requirement, same-origin BFF, signed webhooks, W3C trace metadata only |
| Minimum necessary | Separate portal DTOs, per-agent tool allowlists, claim/tenant filters before retrieval, PHI-safe telemetry |
| Contingency / availability | durable outbox, DLQ/replay, workflow checkpointing, durable SLA timers, backup/DR requirements |
| Device/media/data disposition | retention/disposition policies, approval-gated destructive requests, object-storage lifecycle requirement |
| Security incident procedures | incident response runbook and evidence-preservation procedure |

## Production prerequisites outside code

- Execute and document an organization-specific HIPAA risk analysis.
- Designate security/privacy responsibilities and workforce procedures.
- Execute required BAAs/contracts before PHI reaches vendors.
- Configure production KMS/HSM, secret manager, TLS certificates, backups, DR, centralized SIEM, WAF/API gateway, and approved retention schedules.
- Validate facility/workstation/device/media safeguards.
- Complete legal review of Privacy Rule, Breach Notification Rule, state laws, contractual obligations, and current HHS rulemaking.
