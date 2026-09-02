# Authentication and Tenant Context

MedClaimIQ treats authentication, tenant selection, authorization, and database isolation as separate security decisions. A valid bearer token proves only that an external identity provider authenticated a subject for the configured API audience. It does not grant a role, tenant, claim, or evidence permission by itself.

## Request security flow

```text
Bearer JWT
   │
   ▼
Configured OIDC issuer
   │  discovery + JWKS
   ▼
Signature / iss / aud / exp / iat / scope validation
   │
   ▼
Verified (issuer, subject)
   │
   ▼
Persisted user account
   │
X-Tenant-Id ───────────────┐
   │                       │ selector only
   ▼                       ▼
Persisted active tenant membership
   │
   ▼
Server-resolved Principal
   │
   ├── role
   ├── patient/provider scope
   └── active-state checks
   │
   ▼
Tenant-bound request context
   │
   ▼
Repository filters + PostgreSQL RLS
```

## OIDC/JWT verification

The API uses a fixed configured issuer and audience. Signing keys come only from that issuer's OIDC discovery document and JWKS endpoint. JWT headers such as `jku` or `x5u` are not used to choose remote key sources, preventing a token from redirecting key retrieval to attacker-controlled URLs.

Validation requires the configured asymmetric signing algorithm, a `kid`, signature verification, exact issuer, expected audience, expiry, issued-at time, and the API scope. Clock skew is bounded through configuration. Unknown signing key IDs trigger one JWKS refresh to support normal key rotation.

## External identity key

OIDC `sub` values are unique only within an issuer. MedClaimIQ therefore maps external identities with the compound key:

```text
(issuer, subject)
```

Two identity providers may legitimately issue the same `sub` without colliding in the MedClaimIQ user table.

## Tenant selection is not authorization

Authenticated requests select an operating tenant using `X-Tenant-Id`. The value is never trusted as proof of access. MedClaimIQ resolves the verified external identity to a persisted user and requires an active membership in the selected tenant. A valid JWT cannot obtain access to another tenant merely by changing the header.

Tenant or role claims embedded in a JWT are not used as MedClaimIQ authorization truth. Roles and relationship scopes come from persisted server-side membership state.

## Secure application sessions

MedClaimIQ maintains a lightweight revocable application-session record after token verification. This provides an application-controlled revocation point while continuing to use the enterprise IdP as the source of authentication.

The database does not store raw bearer tokens, refresh tokens, OIDC `sid` values, or JWT `jti` values. Session identifiers are transformed with HMAC-SHA256 using a secret loaded from runtime secret management. Session records store tenant, user, issuer, subject, authentication time, last-seen time, an application-controlled absolute session expiry, revocation metadata, and only hashed external identifiers. Each request still requires a currently valid bearer token.

An OIDC token must contain `sid` or `jti` when application-session enforcement is enabled. If the IdP supplies a stable `sid`, access-token `jti` rotation can occur inside the same application session. A revoked application session cannot be reused even if the external access token has not yet reached its `exp` time.

Optional client fingerprint binding exists but is disabled by default because strict IP/device binding can break legitimate mobile, NAT, proxy, and roaming traffic. When enabled, only a derived value is HMAC-hashed before persistence; raw client IP addresses are not stored by this subsystem.

## Tenant context propagation

After authentication succeeds, middleware stores only the verified server-resolved identity in request state and context variables. Database dependencies read the verified tenant from request state and set PostgreSQL's transaction-local:

```text
app.current_tenant_id
```

Tenant-scoped repositories still add explicit tenant filters. Row-Level Security remains a second line of defense.

## Browser/session boundary

The current backend is implemented as an OAuth/OIDC resource server and expects bearer tokens. It does not persist refresh tokens or issue application login cookies. A production browser deployment should place token acquisition/refresh in an approved OIDC frontend or BFF pattern and use `Secure`, `HttpOnly`, and appropriate `SameSite` cookie controls if a cookie-based BFF session is introduced.

## Operational requirements

Production deployments must configure a real HTTPS issuer, API audience, required scope, strong random HMAC secret from a secret manager, short token lifetimes appropriate to the IdP, IdP-side session termination, application-session revocation, TLS, structured security audit events, rate limiting, and alerting for authentication failures and anomalous tenant-selection attempts.
