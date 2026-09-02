# ADR: Reviewer frontend uses a server-side BFF and human-only decision controls

## Decision

The reviewer application uses Next.js as a backend-for-frontend. OIDC tokens stay server-side in encrypted HttpOnly cookies; browser code calls same-origin BFF routes instead of attaching bearer tokens directly. SSE is proxied through the BFF so browser `EventSource` does not require access-token headers.

The frontend is never authoritative for tenant scope, claim permissions, review locks, evidence provenance, SLA state, MCP approval state, or final claim decisions. It renders and submits intents to the FastAPI backend, which re-enforces all invariants.

## Consequences

This increases route-handler code but prevents bearer-token storage in browser JavaScript and keeps authorization centralized. Review lease tokens are intentionally kept only in component memory. A refresh may require reacquiring the lease, which is preferable to persisting a capability token in web storage.
