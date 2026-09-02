# ADR-002: Deny-First Multi-Tenant Authorization

- Status: Accepted
- Decision owner: MedClaimIQ architecture

## Context

Medical-claim evidence is highly sensitive. A simple role check is insufficient because patients, providers, hospitals, reviewers, auditors, tenant administrators, and platform administrators need fundamentally different scopes. Some workflows also cross organizational boundaries.

## Decision

MedClaimIQ uses centralized deny-first authorization combining RBAC and ABAC.

- Every protected resource has an owning tenant.
- Every authenticated human/service identity is associated with a tenant and role scope.
- Cross-tenant access requires an explicit server-side grant/relationship.
- Patient access requires patient-subject ownership.
- Provider/hospital access requires a server-resolved organizational relationship.
- Reviewer-sensitive actions may require reviewer assignment.
- Tenant administrators and platform administrators have no implicit claim/evidence read permission.
- Authorization decisions are policy-versioned and auditable.

## Why

This reduces cross-tenant data leakage, over-privileged administrative roles, and client-controlled authorization decisions. It also produces an explainable authorization boundary that can be tested independently from APIs and AI workflows.

## Consequences

All future API, worker, RAG, agent, FHIR, and MCP/tool access paths must call the same authorization policy or an equivalent policy-enforcement point. Retrieval filters are defense-in-depth and must never replace authorization.
