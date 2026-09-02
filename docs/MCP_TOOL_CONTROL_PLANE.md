# MCP Tool Control Plane

MedClaimIQ routes every tool call through a deny-by-default control plane. Tool handlers do not authorize themselves and do not receive arbitrary tenant or claim scope from the caller.

## Invocation path

`verified identity -> claim RBAC/ABAC -> registry -> agent allowlist -> input schema -> risk policy -> dry-run/approval -> bounded execution -> output schema -> sanitizer -> provenance -> immutable audit`

### Risk tiers

- **read_only** — deterministic reads only; `read` execution mode.
- **controlled_write** — state-affecting requests; supports dry-run and requires human approval before execute.
- **high_risk_external** — external notification/action boundary; supports dry-run and requires human approval before execute.

## Safety properties

- Tenant and claim identifiers are server-bound and cannot be widened by tool input.
- Agent tool access is allowlisted by registered `AgentName`.
- Input/output are validated with strict Pydantic schemas (`extra=forbid`).
- Write/external tools are idempotent and approval-bound to the exact input SHA-256.
- Approval reuse with changed input is rejected.
- Tool outputs are recursively redacted for secret-bearing keys and suspicious instruction-like text is blocked before it can return to an LLM.
- Bounded retry applies only to transient tool errors; contract/policy failures are never retried past the guard.
- Per-tool circuit breakers fail closed after repeated failures.
- Invocation and health records are append-only and tenant-isolated with PostgreSQL RLS.
- Raw credentials, Authorization headers, notification recipient values, raw approval inputs and raw reviewer comments are not placed in operational audit fields. Approval is bound to the exact schema-valid action by SHA-256.

## External actions

The repository ships a synthetic notification provider contract for local portfolio/demo execution. A production deployment replaces that adapter with an approved enterprise notification provider while preserving the same gateway policy, approval and audit path.

## MCP transport compatibility

The remote endpoint is `POST /mcp` and targets MCP protocol revision `2026-07-28`. It is stateless: there is no `initialize`/`initialized` handshake and no MCP session identifier. Requests must carry `MCP-Protocol-Version` and `Mcp-Method`; `tools/call` additionally requires `Mcp-Name`, and the server rejects header/body mismatches. `server/discover`, `tools/list` and `tools/call` are implemented. Tool lists are deterministic and return private cache hints. W3C `traceparent` is propagated into MedClaimIQ tool telemetry when present.

MedClaimIQ uses `X-MedClaimIQ-Claim-Id` only as a claim selector. It is never authorization proof; the verified user identity and persisted claim RBAC/ABAC checks remain authoritative.
