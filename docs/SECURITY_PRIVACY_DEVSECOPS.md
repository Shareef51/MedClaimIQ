# Security, privacy and DevSecOps architecture

MedClaimIQ centralizes data classes (`public`, `internal`, `confidential`, `phi_restricted`, `secret`) and treats PHI/secrets as prohibited in lower-trust telemetry. The DLP boundary redacts known sensitive keys and deterministic textual identifiers while recording only detector metadata and SHA-256 fingerprints.

Production secrets must come from an approved secret manager. `AWSKMSDataKeyProvider` demonstrates envelope-key generation/decryption: only encrypted data keys and KMS key identifiers may be persisted; plaintext data keys remain memory-only. Local environment-based secret resolution exists only for development.

Security middleware adds abuse limits and API security headers. The frontend BFF already enforces same-origin mutations and HttpOnly encrypted sessions; production should terminate TLS at a hardened ingress/WAF and enforce HSTS/CSP.

Retention is policy/version driven. Destructive data disposition is represented as an approval-gated request; this release deliberately does not add a generic autonomous delete capability. Retention periods in sample configuration are placeholders requiring legal/records-management approval.

Audit exports are redacted, canonicalized JSONL records chained by SHA-256 and signed with an HMAC root manifest. Production should place export objects into retention-locked encrypted object storage and protect signing material in KMS/HSM.

The CI security gate runs secret scanning, local Semgrep rules, Trivy filesystem/config scans, CycloneDX SBOM generation, container image scanning, and on protected main-branch builds produces signed image/provenance artifacts using GitHub OIDC/Sigstore.
