# Release Rollback and Recovery Runbook

## Triggers
Rollback can be initiated for failed Argo Rollouts analysis, post-deployment smoke failure, sustained SLO regression, severe functional regression, security incident, or an approved incident/change-management decision.

## Application rollback
1. Stop further promotion.
2. Identify the last known-good release manifest in `infra/releases/`.
3. Use the protected `Rollback Release` workflow. Production rollback must use the protected production environment approval controls.
4. The workflow writes the known-good immutable digests back to the environment release-values file and commits the Git change.
5. Argo CD reconciles the cluster back to that desired state.
6. Run post-deployment smoke and the required observation window.
7. Preserve release/deployment/audit evidence and open the incident follow-up.

## Database rule
Do not automatically run a destructive database downgrade during application rollback. MedClaimIQ uses expand/contract migrations so a prior application release remains compatible with the expanded schema. If a data/schema recovery is required, use the disaster-recovery runbook with explicit database-owner approval.

## Rollout abort versus durable rollback
Argo Rollouts can automatically abort a canary when analysis fails. That protects traffic immediately. Durable rollback is still represented by a Git revert/promotion to the previous release manifest so Git remains the authoritative desired state.

## Evidence to retain
Release manifest SHA-256, source commit, API/frontend image digests, SBOM/provenance hashes, deployment IDs, Git desired-state commit, Argo CD sync/health evidence, smoke/soak outputs, SLO evidence, approver identity and rollback reason.
