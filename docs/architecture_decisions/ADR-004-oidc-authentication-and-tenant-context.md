# ADR: OIDC Authentication and Verified Tenant Context

## Status

Accepted.

## Decision

MedClaimIQ operates as an OIDC/OAuth2 JWT resource server. JWTs are validated against a configured issuer and audience using an asymmetric algorithm allowlist and keys loaded only from configured OIDC discovery/JWKS endpoints. External identities are keyed by issuer plus subject.

Tenant selection is explicit but untrusted until verified against persisted active membership. Roles, relationship scopes, and tenant authority are resolved from the database rather than copied from client-supplied headers or token role claims. Authenticated request state is then propagated to repository and PostgreSQL RLS context.

The platform persists revocable application-session metadata but never raw bearer or refresh tokens. OIDC session/JWT identifiers are stored only as keyed hashes.

## Consequences

- Identity-provider key rotation is supported without embedding signing secrets in the API.
- A compromised or misconfigured token role/tenant claim cannot silently replace MedClaimIQ authorization state.
- The same OIDC subject value may safely exist under different issuers.
- Tenant spoofing through request headers is denied unless the authenticated identity has persisted membership.
- Application-level session revocation can take effect before access-token expiry.
- Production availability depends on sensible OIDC/JWKS caching and identity-provider operational readiness.
- Browser refresh-token/cookie handling remains outside the resource-server process and must use an approved frontend/BFF design when introduced.
