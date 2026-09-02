# Release Security Certification

MedClaimIQ treats release security certification as a human governance decision backed by immutable technical evidence. Release 107 establishes a human-reviewed release candidate; this release-security layer adversarially tests that exact candidate and cannot certify a different or unreviewed build.

## Blocking security surfaces

The release gate covers cross-tenant access, OIDC/JWT/session/RBAC and IDOR abuse, prompt injection (including indirect retrieved/document/tool-output instructions), RAG poisoning and exfiltration, MCP tool abuse, agent authority escalation, PHI/PII leakage, secret/dependency/SBOM/container/IaC supply-chain controls, API fuzzing, audit-log tampering, and multimodal hidden-instruction attacks.

Critical/high findings, credential leaks, cross-tenant escape, PHI/PII exfiltration, audit-integrity bypass, and production-tool privilege escalation are non-waivable release blockers. Medium/low exceptions require bounded compensating controls, evidence, expiry, and human security-risk approval.

## Evidence chain

`Release 107 human release-candidate decision -> red-team run -> scanner artifacts -> findings/remediation -> eligible human waivers -> deterministic release-security readiness -> compliance evidence pack -> human release-security certification -> separate production promotion approval`

The deterministic fixture matrix is synthetic/de-identified and validates the security harness itself. Gitleaks, Semgrep, dependency, Trivy, SBOM, image-signing/provenance and IaC evidence are expected from CI for a real candidate. This architecture is compliance-oriented engineering evidence, not a legal HIPAA or regulatory certification.
