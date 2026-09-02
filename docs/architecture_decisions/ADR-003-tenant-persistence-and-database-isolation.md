# ADR-003: Tenant Persistence and Database Isolation

## Status

Accepted.

## Decision

MedClaimIQ persists tenants, organizations, user accounts, tenant memberships, and permission-scoped cross-tenant resource grants in PostgreSQL.

A tenant is the security boundary. Organizations are business entities nested inside that boundary. Application repositories must include explicit tenant predicates for tenant-owned records. PostgreSQL Row-Level Security provides a second independent isolation layer using the transaction-local `app.current_tenant_id` setting.

Cross-tenant resource grants are explicit, resource-specific, permission-specific, time-aware, auditable, and revocable. Grant creation and revocation require a persisted actor with grant-management permission in the resource-owning tenant.

## Why

Relying only on role checks or request-supplied tenant identifiers makes accidental cross-tenant data exposure too easy. Separating organization hierarchy from tenant boundaries and enforcing isolation at both application and database layers provides a stronger enterprise model.

## Consequences

- every tenant-owned repository must receive tenant context
- production PostgreSQL roles must not bypass RLS
- background workers must establish tenant context before tenant-scoped queries
- schema migrations must preserve RLS policies
- resource sharing requires explicit durable grants rather than implicit organization relationships
