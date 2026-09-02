# ADR — Managed stateful services with Kubernetes application compute

## Decision
Run MedClaimIQ stateless API, frontend and worker processes on Kubernetes; prefer provider-managed stateful services and treat Qdrant/Kafka endpoints as replaceable managed-service boundaries. PostgreSQL and object storage remain authoritative where defined by the application architecture.

## Consequences
Kubernetes rollouts can be replaced without moving primary claim/evidence state. Multi-AZ availability and PITR use cloud-provider primitives. Qdrant can be rebuilt from PostgreSQL projections, and event outboxes provide replay after broker outages. Infrastructure state is separated from application data state.

## Rejected
Running PostgreSQL/Redis/object storage in the same application cluster by default because cluster-level outages would expand the failure domain and operational burden.
