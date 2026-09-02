# Cloud Infrastructure, High Availability and Disaster Recovery

## Deployment model
MedClaimIQ keeps stateless API/frontend/worker compute on Kubernetes and prefers managed stateful services for PostgreSQL, Redis, object storage, Kafka/Redpanda and Qdrant. This reduces failure domains and avoids operating databases inside the application cluster unless there is an explicit platform-team decision.

The checked-in baseline targets Kubernetes 1.36, with Terraform and Helm used for declarative infrastructure and application deployment. Cloud modules are provided for AWS/EKS and Azure/AKS.

## High availability
- API: minimum three replicas, HPA, zero `maxUnavailable`, zone/host spreading and PDB.
- Frontend: minimum two replicas, HPA, PDB and zone spreading.
- Durable workers: minimum two replicas; application idempotency makes at-least-once work safe.
- PostgreSQL: multi-AZ/zone-redundant with PITR and 35-day backup policy example.
- Redis: multi-AZ managed replication with TLS and encryption.
- Object storage: versioning, encryption and geo/cross-region replication capability.
- Kafka/Qdrant: managed HA endpoints or independently operated multi-zone clusters.

## Network/security
Worker nodes are private. Databases and object storage are not publicly exposed. Ingress terminates TLS and is protected by the cloud WAF/ingress layer. Kubernetes namespaces enforce the `restricted` Pod Security Standard; workloads are non-root, drop capabilities, use read-only filesystems and default-deny NetworkPolicies. Secrets are projected through Secrets Store CSI with AWS/Azure workload identity rather than static cloud credentials.

## Migrations
Helm runs `alembic upgrade head` as a pre-install/pre-upgrade hook. Application schema changes follow expand/contract: add backwards-compatible schema first, deploy compatible code, backfill asynchronously, then remove deprecated schema only in a later release. Destructive migrations are not combined with the rollout that removes compatibility.

## Availability and DR targets
The repository uses portfolio architecture targets of **RTO 60 minutes** and **RPO 5 minutes**. They are targets, not guarantees; production values require business-impact analysis, legal/compliance review and provider capability validation.

## Deployment safety
Use signed immutable image digests, `helm upgrade --install --atomic --wait`, progressive canary/blue-green traffic controls at the ingress/service-mesh layer, automated health/SLO checks and rollback on regression.

## Cloud identity
AWS uses EKS OIDC/IRSA with a service-account-scoped IAM role for Secrets Manager, KMS and S3. The runtime S3 adapter supports the AWS default credential chain so pods do not require static S3 keys. Azure creates an AKS workload-identity federation for the same Kubernetes service account and grants least-privilege Key Vault/Blob roles.

## Provider-specific storage boundary
The core `ObjectStorage` interface is provider-neutral, while the currently implemented evidence adapter is S3-compatible. The Azure Terraform foundation provisions private, GZRS, versioned Blob Storage as the managed-object-storage boundary; production evidence traffic on Azure must either use an approved S3-compatible managed endpoint or add an Azure Blob adapter behind `ObjectStorage` before launch. This limitation is explicit rather than silently substituting static Azure storage keys.

## Progressive delivery
The chart defaults to zero-unavailable rolling updates. `infra/kubernetes/progressive-delivery/README.md` defines canary and blue/green promotion controls using immutable images, SLO/quality/security gates and expand/contract schema compatibility.
