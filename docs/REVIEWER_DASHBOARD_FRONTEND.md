# Reviewer Dashboard Frontend

MedClaimIQ includes a production-style Next.js reviewer application in `frontend/`. The browser-facing application is an operational human-review surface, not a second decision engine. Claim finalization remains in the deterministic FastAPI claim-domain service.

## Security model

The frontend uses an OIDC Authorization Code flow with PKCE. OAuth access and refresh tokens are handled only by the Next.js backend-for-frontend (BFF), AES-GCM encrypted before they are placed in HttpOnly cookies, and never copied to `localStorage` or `sessionStorage`. Backend requests add the bearer token and selected tenant server-side. Mutation routes reject cross-origin requests and the generic BFF exposes only an allowlisted reviewer API surface.

The review lock returned by FastAPI is deliberately kept in React memory. It is not persisted in browser storage. The backend stores only its SHA-256 digest and enforces lease expiry, reviewer ownership, and optimistic claim `status_version` checks.

## Live queue and workbench

`/review` renders the deterministic review queue. A tenant-scoped metadata-only SSE stream listens for review/SLA/guardrail/workflow changes and reloads queue state from the authoritative API. `/review/claims/{claim_id}` uses the existing claim-scoped SSE stream and refreshes the workbench after relevant events.

The workbench exposes:

- immutable original and derived evidence metadata;
- evidence-pack citations, source versions, authority and confidence;
- hospital/FHIR cross-verification;
- evidence graph relationships and contradictions;
- LangGraph workflow status and specialist-agent findings;
- grounding guardrail decisions;
- MCP approval requests;
- SLA deadlines and countdowns;
- reviewer notes and the full claim timeline;
- request-more-evidence and human decision controls.

## Human decision safety

The UI cannot convert an AI recommendation into an automatic decision. A human reviewer must hold an active review lease, submit the current claim `status_version`, select a structured reason code, provide a rationale, and include an evidence snapshot. When the human action disagrees with the advisory AI recommendation, the UI requires an override reason and the backend re-validates the same rule.

## Local development

Copy `frontend/.env.example` to a local untracked environment file and configure the OIDC issuer/client, backend URL, tenant and session secret. Start the FastAPI API and infrastructure first, then run:

```bash
cd frontend
npm install
npm run dev
```

`MEDCLAIMIQ_ALLOW_DEMO_SESSION` exists only for synthetic local development and is ignored in production. Production should use the configured OIDC flow over HTTPS.
