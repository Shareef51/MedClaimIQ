# Release Engineering, GitOps and Environment Promotion

## Principles
MedClaimIQ builds application images once and promotes the exact signed OCI digests through environments. Floating image tags are not part of production desired state. Git is authoritative for deployment intent; Argo CD reconciles Kubernetes to the committed state rather than release CI running ad-hoc `kubectl apply` commands.

## Release object
Every candidate has an immutable JSON release manifest under `infra/releases/`. It records the source commit, signed API/frontend digests, Alembic head, SBOM/provenance hashes and mandatory pre-deployment quality gates. The manifest has its own SHA-256 over the canonical body.

## Promotion
1. Existing CI creates, scans, signs and attests API/frontend images.
2. `release-promotion.yml` verifies the signatures and re-runs the aggregate quality gates.
3. The candidate manifest is created once.
4. Staging desired state is updated to the candidate digests and committed.
5. Argo CD self-heals staging to that Git state.
6. Post-deployment smoke and soak checks must pass.
7. The `production` GitHub Environment requires protected approval before the same digests are committed to production desired state.
8. Production smoke/soak verifies the release after Argo CD reconciliation.

Production should configure required reviewers, prevent self-review, restrict deployment branches/tags and disallow bypass where the GitHub plan supports it.

## Migration compatibility
Application/database releases follow expand/contract. `scripts/check_migration_compatibility.py` inspects candidate Alembic `upgrade()` functions newer than the deployed revision and blocks destructive upgrade calls. A schema contraction is a separate release after old application versions have stopped serving traffic.

## Progressive delivery
Argo Rollouts examples support canary and blue/green. The canary advances through 10%, 25%, 50% and 100% while running health/error-rate/p95-latency analyses. Failed analysis aborts the Rollout. Blue/green keeps automatic promotion disabled and runs pre/post-promotion analysis.

## Drift
Staging self-heals automatically. Production is intentionally manual promotion, but `gitops-drift-detection.yml` refreshes Argo CD state on a schedule and fails when an application is OutOfSync or unhealthy. The remediation path is Git reconciliation, not an undocumented manual cluster change.

## Auditability
A PostSync release-audit Job writes the immutable release manifest identity and final deployment record into tenant-isolated PostgreSQL tables. Audit records store image digests, Git/desired-state SHAs, migration head, release manifest hash, strategy, environment and rollback metadata.
