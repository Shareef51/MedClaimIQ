# ADR: GitOps and immutable release promotion

## Decision
MedClaimIQ builds each application artifact once, identifies it by signed OCI digest, and promotes the same digests from staging to production. Git is the deployment source of truth and Argo CD performs reconciliation. Production promotion requires environment protection/human approval. Argo Rollouts controls progressive traffic movement and automated analysis-based aborts.

## Why
Rebuilding between environments changes the artifact being validated. Direct imperative deployments create hidden state and weak auditability. Immutable digests plus declarative desired state make staging evidence meaningful, enable deterministic rollback, and provide an auditable chain from source commit to running workload.

## Database consequence
Database migrations use expand/contract. Application rollback does not automatically imply database downgrade.
