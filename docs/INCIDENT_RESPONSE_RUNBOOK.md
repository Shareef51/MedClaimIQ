# Incident response runbook

1. **Detect and classify.** Open a security incident for suspected PHI disclosure, credential compromise, tenant-boundary failure, malicious tool execution, supply-chain compromise, ransomware, or audit-integrity failure.
2. **Contain.** Revoke affected OIDC/application sessions; disable tenant/vendor integrations; rotate secrets/keys; quarantine affected evidence; pause high-risk MCP tools or event consumers as appropriate.
3. **Preserve evidence.** Export relevant append-only audit history using the hash-chain export, preserve trace IDs, object VersionIds/SHA-256 values, container image digests, SBOM/provenance, and timestamps. Never copy raw PHI to tickets/chat.
4. **Eradicate.** Patch root cause, revoke credentials/tokens, rebuild from signed trusted images, re-index rebuildable vector projections when needed.
5. **Recover.** Restore from verified backups, replay durable outboxes/DLQs, resume workflows/timers, validate tenant isolation and integrity gates.
6. **Notify/escalate.** Security/privacy/legal teams determine contractual and regulatory notification obligations; the software does not make legal breach determinations.
7. **Post-incident.** Record lessons learned, update threat model/control mapping/golden adversarial tests, and block release until the security readiness gate passes.
