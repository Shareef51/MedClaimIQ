# Production Performance, Resilience, Disaster Recovery & Operational Go-Live Readiness

This release gate verifies that the MedClaimIQ release candidate is operationally fit for human go-live review after the human release-candidate and release-security decisions have been recorded.

## Required evidence

The operational evidence pack covers production-scale load/stress/soak tests, multi-tenant noisy-neighbor isolation, AI/RAG/agent latency and cost SLOs, PostgreSQL/Redis/Kafka/vector/object-store resilience, LLM provider outage/fallback behavior, Kubernetes pod/node/AZ disruption, backup/restore integrity, measured RPO/RTO, failover/failback, autoscaling and capacity headroom, observability/alerts/runbooks/on-call routing, and incident-response exercises.

## Non-bypassable blockers

Tenant-isolation failure, data loss/corruption, failed backup restore, RPO/RTO breach, unsafe model fallback and unresolved Sev-1 operational risk block go-live readiness. AI, agents, RAG, MCP and workers can measure, monitor and recommend only; they cannot accept risk, certify operational readiness or promote the release to production.

## Authority chain

`human release candidate -> human security certification -> operational drills -> deterministic gates -> human operational readiness certification -> separate human production promotion`
