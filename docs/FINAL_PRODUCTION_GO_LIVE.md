# MedClaimIQ Final Production Go-Live Governance

The final production release uses a human-governed process. Production promotion requires immutable human release-candidate approval, security certification and operational-readiness certification.

## Final release path
1. Freeze immutable commit, image digest, SBOM digest, configuration fingerprint and Alembic head.
2. Approve the production change window and GitOps promotion plan.
3. Validate database connectivity, backup checkpoint, migration preflight, secrets/configuration, tenant isolation and rollback artifact.
4. Human go-live authority approves or rejects release.
5. Human release operator executes GitOps promotion with canary/progressive rollout.
6. Run smoke tests and synthetic claim journey; verify API/UI, RAG, LangGraph agents, MCP, event stream and datastores.
7. Human final-release certifier records certification after deployment evidence is complete.
8. Operate hypercare command center with SLO/error-budget, incident and rollback monitoring.
9. Human operations authority closes hypercare only after the stability window passes with no Sev-1 blocker.

AI/agents may assess, summarize, monitor and recommend rollback, but may not approve go-live, promote production, certify the release or close hypercare.
