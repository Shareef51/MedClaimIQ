# MedClaimIQ Security Policy

MedClaimIQ is designed for synthetic or de-identified portfolio/demo data unless an operator has established the legal, contractual, privacy, security, and operational controls required for real regulated data.

## Release security rules

- Critical and high security findings block release.
- Credential/secret leakage, cross-tenant escape, PHI/PII exfiltration, audit-integrity bypass, authorization bypass, and production-tool privilege escalation are non-waivable.
- Medium/low exceptions require documented compensating controls, evidence, expiry, and human security-risk approval.
- AI, agents, RAG, MCP and workers may detect, summarize, test, and recommend; they cannot approve security waivers, accept security risk, issue release security certification, or promote to production.
- Release security certification must reference the immutable human Release 107 release-candidate decision and the immutable red-team evidence bundle.

## Secure development baseline

Use OIDC/JWT signature verification, tenant-scoped persistence/retrieval/tool execution, minimum-necessary data access, external secret managers/KMS in production, TLS, non-root/read-only containers, network policies, immutable audit evidence, Gitleaks, Semgrep, dependency scanning, CycloneDX SBOM, container/IaC scanning, signed images/provenance, and human-controlled production promotion.

Security evidence should never contain raw patient data, production credentials, or unrestricted secrets.
