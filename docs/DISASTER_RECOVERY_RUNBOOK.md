# Disaster Recovery Runbook

## Objectives
Architecture targets: RTO 60 minutes and RPO 5 minutes. Validate these with real restore exercises before production approval.

## Declare
1. Incident commander declares DR and freezes nonessential deployments.
2. Record incident/trace/time boundaries and preserve audit evidence.
3. Determine whether the primary database, object store, Kafka/Qdrant projections, Kubernetes region or identity provider is affected.

## Restore order
1. Identity, network, KMS/Key Vault and secrets-management access.
2. PostgreSQL from point-in-time recovery to an approved recovery timestamp.
3. Object storage from replicated/versioned data; verify representative SHA-256 evidence provenance.
4. Redis starts empty if necessary; it is treated as cache/ephemeral coordination where application contracts permit.
5. Qdrant is rebuilt from authoritative PostgreSQL RAG chunks/manifests if managed recovery is unavailable.
6. Kafka/Redpanda is recovered from managed replication/backups; transactional PostgreSQL outboxes are replayed for business events not confirmed as published.
7. Deploy Kubernetes application using signed immutable image digests.
8. Run schema/current-version verification, health checks, synthetic claim read, FHIR mock/safe connectivity, RAG source checksum checks and authorization isolation tests.
9. Open traffic gradually and monitor error/latency/SLOs.

## Failback
Failback is a separate controlled change. Reconcile database/object versions, pause writes if needed, validate replication lag, switch traffic, then retain the recovery environment until audit sign-off.

## Required evidence from every exercise
Recovery timestamp, backup IDs, database consistency result, evidence object hash checks, RAG rebuild status, outbox backlog/replay count, authorization/tenant-isolation result, actual RTO/RPO achieved and remediation actions.

## Automated recovered-environment smoke check
Run `PYTHONPATH=backend python scripts/run_restore_smoke.py` against the recovered PostgreSQL environment. Set `RESTORE_VERIFY_OBJECT_SAMPLE=true` only after object-storage credentials/workload identity are available; the script then re-hashes a representative accepted evidence object and compares it with persisted provenance.
