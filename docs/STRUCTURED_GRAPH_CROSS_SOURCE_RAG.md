# Structured, Graph and Cross-Source RAG

MedClaimIQ uses four complementary retrieval paths: hybrid vector retrieval, typed SQL retrieval, versioned FHIR retrieval, and bounded GraphRAG traversal. PostgreSQL remains authoritative for structured claim data and evidence relationships; Qdrant remains a rebuildable retrieval projection.

## Safe structured retrieval

The system never asks an LLM to emit executable SQL. A deterministic planner selects from whitelisted facts (`claim`, `claim_lines`, `policy`, `encounter`, `provider`, `contradictions`), and repository methods compile those facts to tenant- and claim-scoped SQLAlchemy statements. Row limits and service-date constraints are enforced before execution.

## FHIR retrieval

FHIR evidence comes from immutable versioned snapshots already accepted through the FHIR gateway. Each result includes logical resource identity, `versionId`, snapshot ID, source URL, content hash and authority metadata.

## GraphRAG

GraphRAG traverses only canonical entities and evidence edges for the authenticated claim. Traversal has hard depth and edge ceilings and optional relationship/as-of filters. The LLM cannot create authoritative graph edges or supply arbitrary graph query language.

## Evidence fusion

Results are normalized into a common evidence contract with authority rank, confidence and unified citations. Duplicate evidence is collapsed deterministically. Open contradiction records are attached to the evidence pack rather than hidden or resolved by generation. Material unresolved contradictions lower the pack confidence and remain visible to downstream agents and human reviewers.

## Immutable evidence packs

Each cross-source search creates an immutable evidence-pack snapshot. PostgreSQL stores the query hash, retrieval coverage, evidence hashes/citations, source provenance and contradiction references. Raw reviewer queries and duplicated evidence text are not persisted in these telemetry tables by default.

Evidence packs are decision-support inputs only. They never authorize an autonomous final claim approval or denial.
