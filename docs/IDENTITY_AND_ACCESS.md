# Identity, Personas, Roles, Permissions, and Tenant Isolation

MedClaimIQ uses authentication and authorization as separate concerns. Identity providers prove who a caller is; the MedClaimIQ authorization engine decides what that identity may do with a specific resource.

## Personas

| Persona | Primary responsibilities | Access boundary |
|---|---|---|
| Patient | Submit a claim, upload requested evidence, view their own claim status | Own patient-subject scope only |
| Provider | Submit/support claims and evidence for the provider organization | Provider relationship + explicit tenant sharing |
| Hospital Admin | Verify hospital-side records and evidence | Hospital relationship + explicit tenant sharing |
| Claims Reviewer | Review evidence, inspect AI findings, request evidence, record the human claim decision | Payer tenant; decision actions are assignment-aware |
| Auditor | Inspect audit history and control evidence | Read-only governance scope |
| Tenant Admin | Manage tenant members, roles, grants, and tenant settings | No implicit claim/evidence access |
| System Admin | Operate the MedClaimIQ platform and tenant lifecycle | No implicit medical claim/evidence access |

## Authorization model

The policy is **deny by default** and combines:

1. **RBAC** — each role has an explicit permission set.
2. **ABAC** — access also depends on tenant ownership, patient ownership, provider relationships, reviewer assignment, tenant status, and explicit sharing grants.
3. **Resource isolation** — each protected record is owned by a tenant and must be resolved server-side before authorization.
4. **Explicit cross-tenant sharing** — provider/hospital collaboration is never inferred from a request. It requires a persisted, auditable grant or resource relationship.
5. **Separation of duties** — tenant/platform administrators do not automatically get access to medical claim evidence.

## Tenant model

A tenant represents an organization boundary such as a payer, provider organization, hospital, TPA, or isolated demo organization. All domain records will carry an owning `tenant_id` or inherit one from an owning aggregate.

Cross-tenant workflows are represented as explicit resource grants. A grant must eventually include:

- grant ID
- owner tenant
- grantee tenant
- resource or relationship scope
- granted permissions
- issuer
- purpose/reason
- created/expiry timestamps
- revoked timestamp/status
- audit correlation ID

The current code models a resolved `ResourceGrant` with grantee tenant, active/revoked state, and permission scope. Grant expiry/revocation timestamps will be persisted with the database identity schema; only an active, permission-matching grant can cross the tenant boundary.

## Claim-review separation of duties

AI may produce evidence-backed recommendations, but only a claims reviewer with the relevant permission and resource scope may record a human decision. Reviewer-sensitive actions are assignment-aware to reduce unintended concurrent or unauthorized review activity.

## Trust rules

Authorization attributes are **server-derived**:

- authenticated `principal` comes from verified session/token claims plus server-side identity data;
- resource ownership and relationships come from the database;
- explicit sharing grants come from the grant store;
- clients never get to declare their own role, tenant ownership, patient ownership, provider relationship, or cross-tenant grant.

## Policy version

Current authorization contract: `medclaimiq.authz.v1`.

Policy decisions return a machine-readable allow/deny reason so security/audit telemetry can explain why access was granted or rejected without logging medical evidence.
