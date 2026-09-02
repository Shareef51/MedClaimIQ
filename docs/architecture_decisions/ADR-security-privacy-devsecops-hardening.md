# ADR: Security controls are fail-closed and independently enforceable

## Decision
Security/privacy controls that affect authorization, PHI release, destructive retention, external actions, or release readiness are deterministic application/CI controls rather than LLM decisions. External security/observability vendors are non-authoritative projections. Production secrets and encryption keys are resolved by a dedicated secret/KMS boundary.

## Consequences
- The project can be evaluated without trusting a model to judge its own security.
- PHI-safe telemetry and minimum-necessary DTOs reduce secondary data stores.
- Retention execution and high-risk actions require explicit approval.
- Supply-chain artifacts can be verified independently from source code.
- “HIPAA-ready” means technical preparation only; compliance remains an organizational/legal responsibility.
