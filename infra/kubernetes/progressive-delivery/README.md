# Progressive delivery

MedClaimIQ supports Argo Rollouts canary and blue/green patterns. The reference controller baseline is Argo Rollouts v1.9.1. Release images are immutable digests produced and signed before promotion.

## Canary
The reference canary shifts traffic 10% → 25% → 50% → 100%. Each intermediate step runs the `medclaimiq-api-release-slo` AnalysisTemplate. Analysis failure aborts the rollout; Git remains the source of truth, so durable rollback is completed by reverting the environment release-values file to a known-good release manifest.

## Blue/green
The preview service receives the new digest first. Promotion is manual and protected; pre/post-promotion analyses must pass. `autoPromotionEnabled: false` prevents an unattended cutover.

## Database compatibility
Progressive delivery assumes expand/contract schema compatibility. A release containing destructive Alembic upgrade operations is blocked by `scripts/check_migration_compatibility.py`. Contract migrations are shipped only after old application versions are no longer serving traffic.
