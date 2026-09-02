# MedClaimIQ Frontend Production Readiness

MedClaimIQ presents two intentionally different product experiences: a secure reviewer operations console and a simplified patient/provider claim portal. The reviewer experience prioritizes evidence provenance, human authority, operational visibility and governed workflows; the external portal exposes claim status, document response, released notices and authorized provider recovery workflows without exposing internal reasoning.

## Final experience architecture

- Enterprise OIDC remains the production sign-in path through the Next.js BFF and encrypted HttpOnly cookies.
- Synthetic persona access is available only when explicitly enabled outside production.
- Reviewer navigation uses grouped desktop navigation and a mobile drawer with role-scoped destinations.
- Patient and provider identities are routed to the external portal and cannot enter reviewer workspaces through normal navigation.
- Provider-only dispute and recovery modules are not rendered for patient personas.
- FHIR, evidence relationships and AI orchestration are grouped as Advanced Investigation rather than exposed as primary claims terminology.
- Browser prompt/alert workflows are replaced by accessible evidence-aware dialogs.
- Regulatory and financial APIs use typed runtime-validated contracts rather than untyped escape hatches.
- Operational dashboards surface claim risk, SLA aging, recovery, regulatory exposure, RAG quality and AI latency.
- Global, reviewer and portal loading/error boundaries fail visibly without silently replaying business mutations.
- Unknown routes use an explicit not-found experience with safe workspace navigation.

## Responsive and accessibility expectations

The reviewer console supports a desktop sidebar and compact mobile navigation. Both reviewer and portal experiences include skip navigation, visible keyboard focus, reduced-motion behavior, accessible dialog semantics, focus containment, Escape handling, table captions where operational tables are used, explicit status/error regions and retry-oriented failure states.

## Build verification boundary

The source package intentionally excludes `node_modules`. The frontend dependency versions and Node/npm runtime are pinned in `frontend/package.json`. In an environment with dependency access, the definitive frontend gate is:

```text
npm install
npm run typecheck
npm run build
```

This packaged validation does not claim a Next.js production build when the dependency registry is unavailable. Source syntax, route contracts, UI regression tests, release governance tests and static security/UX checks are validated independently.
