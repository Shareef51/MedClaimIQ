# ADR: Deny-by-default MCP/tool control plane

## Decision

All model/agent and human-triggered tools are registered centrally and invoked through one policy gateway. Agents cannot call arbitrary functions, URLs, SQL, or lifecycle mutators. Tool schemas, permissions, agent allowlists, risk tiers, approval requirements, idempotency, retries, circuit breaking, output sanitization and provenance are enforced outside the model.

## Consequences

This adds control-plane code and approval state, but makes tool behavior replayable, inspectable and fail-closed. High-risk actions remain human-authorized and the LLM never becomes the source of authorization truth.
