# ADR: External portal information minimization

**Decision:** Patient/provider portal responses are separately composed and never reuse the internal reviewer workbench DTO.

**Rationale:** The reviewer workbench contains fraud/risk signals, contradictions, agent findings, reviewer notes, and governance metadata that external identities do not need. Reusing that response and hiding fields in React would make the browser a security boundary. The backend instead emits a purpose-built external DTO and allowlisted SSE stream.

**Consequences:** External views are relationship-scoped and least-privilege; new internal fields cannot leak into the portal by default. Portal uploads remain bound to the quarantine-first ingestion service.
