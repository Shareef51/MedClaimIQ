# Enterprise Tenancy and Persistence

MedClaimIQ separates business organization structure from the security boundary used to isolate data.

## Tenant boundary

A **tenant** is the top-level security and data-isolation boundary. Tenant status is persisted and participates in authorization decisions. Suspended or disabled tenants are not treated as active principals.

## Organizations

Organizations are business entities that exist inside a tenant. Examples include a payer operations group, hospital, provider organization, department, or third-party administrator. Organizations can form a parent/child hierarchy while remaining inside one tenant.

This distinction supports enterprise structures without using organization hierarchy as a substitute for tenant isolation.

## User accounts and memberships

User identity is stored once in `user_accounts`. Access to a tenant is represented by a `tenant_membership` containing the tenant, role, membership status, and optional patient/provider organization scope.

Authorization principals are reconstructed from persisted tenant, account, and membership state. Client requests must never be trusted to declare their own role, tenant, patient identity, organization relationship, or grant state.

## Resource grants

Cross-tenant access is deny-by-default. A resource grant persists:

- owner tenant
- grantee tenant
- resource type and identifier
- exact permission scope
- activation and expiry timestamps
- active/revoked state
- grant creator
- revocation actor and reason

Only an active member of the owning tenant whose role includes `tenant_grant_manage` may create or revoke a grant through the tenancy service.

## Isolation strategy

MedClaimIQ uses two independent controls:

1. Tenant-scoped repository predicates in application code.
2. PostgreSQL Row-Level Security as database defense-in-depth.

Application transactions set `app.current_tenant_id` as a transaction-local PostgreSQL setting. RLS policies on organizations, memberships, and resource grants restrict which rows can be read or written. Resource grant reads may be visible to the owner or explicit grantee tenant, while writes remain owner-only.

The production database application role must be a non-superuser role that does not bypass RLS.

## Transaction boundary

Service methods flush changes but do not silently commit. The API/application unit of work owns commit and rollback so multi-step operations can be atomic.

## Persistence tables

```text
tenants
  ├── organizations
  └── tenant_memberships ── user_accounts

resource_grants
  ├── owner_tenant_id ── tenants
  ├── grantee_tenant_id ── tenants
  ├── resource_type + resource_id
  └── permission/time/revocation metadata
```

## Security invariants

- no membership can reference an organization from another tenant
- one user has at most one membership per tenant in the current role model
- cross-tenant grants cannot target the owner tenant
- grant permissions are explicit and do not imply additional permissions
- expired, scheduled, or revoked grants are not effective
- administrative roles do not gain implicit claim/evidence access
- RLS complements authorization; it does not replace application authorization
