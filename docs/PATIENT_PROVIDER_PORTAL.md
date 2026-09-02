# Patient and Provider Portal

MedClaimIQ exposes a deliberately minimized external experience for patient, provider, and hospital operational identities. Access is resolved from persisted membership attributes and claim relationships; a client-supplied patient/provider identifier is never trusted as authorization.

The portal shows only claim status, requested documents, the signed/quarantined upload flow, acknowledgement codes, safe hospital/provider verification status, active deadlines, and a reduced claim timeline. Internal fraud/waste signals, denial-risk reasoning, specialist-agent findings, critic output, GraphRAG contradictions, reviewer notes, MCP internals, and prompt/guardrail details are not part of the portal contract.

Requested documents use the existing secure evidence-ingestion path. Completing an upload means **received for security processing**, not accepted evidence. Malware, magic-byte/MIME, SHA-256, object-version, and quarantine checks must complete before downstream extraction, RAG, or agent consumption.

Realtime portal updates are emitted through an allowlisted claim SSE stream that minimizes payload fields. The internal realtime stream remains separate.
