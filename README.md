# MedClaimIQ

**Real-Time Multimodal Agentic Multi-RAG Medical Claims Verification & Evidence Intelligence Platform**

MedClaimIQ is a production-style AI engineering project for evidence-backed medical-claims verification. It is designed for synthetic or de-identified portfolio data and demonstrates multimodal document intelligence, FHIR-aware structured retrieval, Multi-RAG, LangGraph orchestration, guardrails, real-time workflows, human review, evaluation, LLMOps, and cloud-ready engineering.

## AI quality engineering

MedClaimIQ includes a deterministic AI/RAG evaluation harness with versioned synthetic golden datasets, retrieval/citation/grounding/security/agent/workflow/tool/FHIR/contradiction metrics, baseline regression budgets, zero-tolerance safety cases, retrieval ablations, JSON/HTML reports, immutable tenant-scoped evaluation history, and CI release gates. See `docs/AI_RAG_EVALUATION_QUALITY.md`.


## Product boundary

MedClaimIQ supports human reviewers; it does **not** diagnose, recommend treatment, or autonomously issue a final claim approval/denial. Material AI findings must be evidence-backed and traceable to source records.

## Production capabilities

The repository includes:

- explicit business and safety scope
- claim lifecycle/state machine
- audit/provenance requirements
- FastAPI service skeleton
- typed configuration
- versioned health API
- local PostgreSQL, Redis, and MinIO dependencies
- executable tests
- architecture decision records
- enterprise personas and tenant boundaries
- deny-first RBAC + ABAC authorization contracts
- patient/provider relationship scoping
- explicit cross-tenant access grants
- assignment-aware reviewer actions
- separation of tenant/platform administration from claim-evidence access
- machine-readable authorization decision reasons
- persisted enterprise tenants and business organizations
- persistent user accounts and tenant memberships
- server-resolved authorization principals from database state
- permission-scoped cross-tenant resource-grant persistence
- scheduled, expiring, and revocable resource grants with actor metadata
- tenant-scoped repositories plus PostgreSQL Row-Level Security defense-in-depth
- Alembic migration foundation and synthetic tenancy seed data
- OIDC/OAuth2 bearer JWT resource-server authentication
- OIDC discovery and JWKS verification with asymmetric algorithm allowlisting
- external identity mapping keyed by issuer plus subject
- persisted principal resolution; token role/tenant claims are not authorization truth
- verified tenant-selection middleware with active membership enforcement
- request-scoped tenant propagation into PostgreSQL RLS context
- revocable application sessions with HMAC-hashed OIDC/JWT identifiers
- no raw access-token or refresh-token persistence
- tenant-isolated patient, provider, policy, encounter, claim and claim-line persistence
- claim-centered evidence artifacts with SHA-256 deduplication and source provenance
- append-only evidence lineage for derived artifacts and future RAG chunk provenance
- canonical claim lifecycle transitions with row locking, status versions and replay-safe idempotency
- append-only claim status events and governance audit events
- persisted human-review decisions with reviewer assignment and evidence snapshots
- automated workflows cannot directly finalize a claim from human review
- claim/evidence PostgreSQL Row-Level Security and immutable-event database triggers
- relational foundations for future structured RAG and relationship/GraphRAG retrieval
- production Multi-RAG foundation with Claim, Policy, Hospital, Invoice, Coding, Historical Claims and Evidence domains
- parent/child chunk persistence with page, bounding-box and timestamp citation preservation
- OpenAI embedding adapter with configurable `text-embedding-3-large` dimensions, batching and Redis-compatible caching
- Qdrant domain collections with tenant/claim/ACL/entity/source-version payload filtering
- deterministic Qdrant UUID point IDs and replay-safe vector upserts
- PostgreSQL-authoritative chunk/index manifests with versioned re-index and delete flows
- persistent RAG index jobs, exponential retry and terminal dead-letter records
- dense retrieval with precise child matches and parent-context hydration
- hybrid dense + sparse/BM25-compatible retrieval using named Qdrant vectors
- deterministic healthcare query planning, domain routing, multi-query expansion and decomposition
- Reciprocal Rank Fusion across dense/sparse channels, query variants and RAG domains
- evidence-aware reranking using source authority, evidence confidence, exact terms and temporal alignment
- source diversification and citation-safe contextual compression
- retrieval confidence/coverage scoring with explicit no-evidence outcomes
- safe fallback routing that never relaxes tenant, claim or server-derived ACL filters
- append-only, tenant-RLS retrieval telemetry without raw query persistence by default

- isolated multimodal document-intelligence worker boundary
- layout-aware PDF extraction contracts with page/bounding-box citations
- OCR extraction contracts with per-unit confidence and coordinates
- timestamped audio transcription and video/keyframe extraction contracts
- structured table units rather than prose-only flattening
- normalized extraction manifests stored as non-authoritative derived evidence
- explicit `DERIVED_FROM` provenance from every normalized artifact to accepted evidence
- extraction retry/backoff and persistent dead-letter replay records
- append-only extraction units plus tenant Row-Level Security



## Cloud infrastructure, HA and disaster recovery

MedClaimIQ includes Terraform foundations for AWS/EKS and Azure/AKS plus a hardened Helm chart for API, frontend and durable workers. The cloud model uses Kubernetes 1.36 as the checked-in baseline, private/managed data services, Secrets Store CSI/workload identity, TLS/WAF ingress boundaries, default-deny NetworkPolicies, restricted pod security, HPA/PDB/topology spread, pre-upgrade Alembic migrations, PostgreSQL PITR, versioned object storage and restore-readiness checks. The documented RTO 60m / RPO 5m values are architecture targets rather than guarantees. See `docs/CLOUD_INFRASTRUCTURE_HA_DR.md` and `docs/DISASTER_RECOVERY_RUNBOOK.md`.

## Run locally

### 1. Start infrastructure

```bash
docker compose up -d
```

### 2. Apply database migrations

```bash
cd backend
alembic upgrade head
```

Optional synthetic tenant seed after installing the backend package:

```bash
PYTHONPATH=backend python scripts/seed_tenancy.py
PYTHONPATH=backend python scripts/seed_claim_domain.py
```

### 3. Start API

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -e '.[dev,document-intelligence]'
uvicorn app.main:app --reload --port 8000
```

### 4. Verify

```bash
curl http://localhost:8000/api/v1/health
```

Expected response:

```json
{
  "service": "medclaimiq-api",
  "status": "ok",
  "environment": "local"
}
```

## Authentication

Protected API routes require an OIDC bearer token and an explicit tenant selector:

```bash
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "X-Tenant-Id: tenant-demo-payer"
```

`X-Tenant-Id` selects an operating tenant but never grants access by itself; the verified OIDC identity must have a persisted active membership in that tenant.

## Repository direction

```text
MedClaimIQ/
├── backend/          # FastAPI API, persistence models, repositories and migrations
├── sample-data/      # Synthetic/de-identified demo fixtures
├── config/           # Versioned policy/configuration contracts
├── docs/             # Product, safety, identity/access and ADR documentation
├── scripts/          # Local development utilities
├── docker-compose.yml
└── .env.example
```


## Secure evidence ingestion

Evidence uploads use a quarantine-first S3/MinIO workflow. The API creates an idempotent upload session and a pre-signed POST whose policy binds the tenant, claim, upload session, content type, and exact declared content length. Completion only records that an object is ready for asynchronous verification.

The ingestion worker computes the server SHA-256, detects actual media type from bytes, checks for MIME spoofing, streams the object through ClamAV, deduplicates by claim/content hash, and only then promotes clean content into the accepted storage prefix. Raw client filenames are not persisted and are never used in object keys. Append-only processing events plus a transactional outbox prepare the workflow for Kafka/Redpanda delivery without dual-write risk.

Architecture details are in `docs/SECURE_MULTIMODAL_INGESTION.md` and `docs/architecture_decisions/ADR-006-quarantine-first-evidence-ingestion.md`.

## Multimodal document intelligence

Accepted evidence is parsed outside the API process. Parser outputs become citation-addressable extraction units and a normalized derived evidence artifact with explicit lineage to the immutable original. See `docs/MULTIMODAL_DOCUMENT_INTELLIGENCE.md`.

## Healthcare interoperability

MedClaimIQ includes an R4-compatible synthetic FHIR hospital boundary for Patient, Encounter, Coverage, Claim, ExplanationOfBenefit, DocumentReference, Organization, and Practitioner resources. External healthcare records are persisted as immutable versioned evidence with provenance, canonical normalization, conservative identity reconciliation, hospital-vs-upload cross-verification, and transactional healthcare events. SMART backend-services authentication is represented by a private-key token-provider boundary; production private keys belong in a secret manager.


## Evidence intelligence

- **Unified evidence graph:** deterministic canonical identities, source-version mappings, temporal relationships, claim-line crosswalks, contradiction preservation, and RAG-ready provenance metadata.

## Multi-RAG retrieval foundation

MedClaimIQ separates Claim, Policy, Hospital, Invoice, Coding, Historical Claims, and Evidence retrieval domains. PostgreSQL remains authoritative for chunk text, provenance, source versions and vector projection manifests; Qdrant is a rebuildable hybrid-vector projection with named dense and sparse vectors. Retrieval is filtered by tenant/claim/ACL metadata inside Qdrant before hits are returned. Child/table/transcript chunks are embedded for precision while parent chunks provide context hydration without losing the matched citation anchor. See `docs/PRODUCTION_MULTI_RAG_FOUNDATION.md` and `docs/ADVANCED_HYBRID_MULTI_RAG_RETRIEVAL.md`.

Local infrastructure includes Qdrant on ports `6333`/`6334`. Configure `OPENAI_API_KEY` through local environment injection or a production secret manager before running live embedding jobs.

- Structured SQL/FHIR RAG, bounded GraphRAG traversal, contradiction-aware cross-source evidence fusion, unified citations, and immutable evidence-pack snapshots.

## Grounded RAG safety boundary

Cross-source evidence is treated as untrusted data before it can reach any future LLM or agent. The API includes deterministic indirect prompt-injection screening, evidence-quality and answerability gates, citation-to-evidence verification, unsupported-claim and numeric/medical-code checks, contradiction-aware release controls, bounded self-corrective retrieval, and immutable guardrail telemetry. See `docs/RAG_GROUNDING_GUARDRAILS.md`.

## Durable multi-agent orchestration

MedClaimIQ uses LangGraph for stateful, durable specialist-agent coordination. Each workflow is bound to one tenant, claim, immutable evidence pack, and stable LangGraph thread ID. A deterministic supervisor selects specialist work, independent agents fan out in parallel, reducer-backed results fan in for evidence fusion and critic review, and high-risk conditions pause at durable human-review checkpoints.

Production checkpointing uses PostgreSQL through `langgraph-checkpoint-postgres` with strict MessagePack deserialization enabled. Agent findings and execution events are auditable, while raw evidence remains in the immutable evidence pack rather than being copied into orchestration checkpoints.

Agents cannot mutate authorization, tenant scope, canonical evidence relationships, or final claim outcomes. Human approval/denial continues through the deterministic claim-domain lifecycle. See `docs/LANGGRAPH_DURABLE_AGENT_ORCHESTRATION.md`.

## Specialist agent reasoning layer

The agent runtime includes thirteen evidence-bound specialist agents for intake, hospital/FHIR verification, invoice verification, eligibility, policy, coding, duplicate-claim signals, fraud/waste signals, denial-risk signals, evidence fusion, critique, advisory decision support, and human-review routing. Agent model output is schema-constrained, evidence references are validated against the immutable evidence pack, tool access is read-only and allowlisted, and final claim decisions remain exclusively human-authorized deterministic workflow actions.

## End-to-end agent execution

The durable workflow now executes the complete specialist chain: evidence-pack rehydration and SHA-256 validation, deterministic supervision, intake, parallel specialist fan-out, reducer-backed fan-in, evidence fusion, critic review, advisory decision support, human-review routing, and a LangGraph interrupt backed by the PostgreSQL checkpointer. Specialist failures are isolated per branch and workflow events can be tailed over authenticated SSE using sequence cursors. See `docs/END_TO_END_AGENT_EXECUTION.md`.

## MCP tool control plane

All external/tool-capable operations pass through a deny-by-default MCP gateway with typed schemas, persisted tenant/claim authorization, per-agent allowlists, risk tiers, dry-run support, human approval for controlled writes and external actions, idempotency, bounded retries, circuit breaking, output sanitization, provenance, and immutable audit telemetry. The remote `POST /mcp` transport targets MCP protocol revision `2026-07-28` and uses the stateless `server/discover`, `tools/list`, and `tools/call` request model. See `docs/MCP_TOOL_CONTROL_PLANE.md`.

## Real-time event backbone

MedClaimIQ uses PostgreSQL transactional outboxes plus the Kafka API for asynchronous coordination across claim lifecycle, evidence processing, FHIR integration, LangGraph workflows, and MCP tool execution. The local stack uses Redpanda and Redpanda Console. Events are partitioned by `claim_id`, consumers are idempotent through persisted receipts, retries are bounded through retry topics, exhausted events enter a replayable DLQ, and authenticated clients can follow claim-scoped operational events over SSE.

Run the outbox relay after infrastructure and migrations are ready:

```bash
cd backend
PYTHONPATH=. python -m app.workers.outbox_relay
```

The system intentionally describes delivery as **at least once** rather than claiming end-to-end exactly-once semantics. Event payloads contain operational references/metadata rather than raw medical documents or model prompts. See `docs/REAL_TIME_EVENT_DRIVEN_BACKBONE.md`.


## Deadline operations

MedClaimIQ includes durable tenant-timezone SLA timers, business calendars, warning/breach events, human-review escalation, approval-gated MCP notifications, and real-time countdown metadata.

## Human review operations

The reviewer backend includes a deterministic priority queue, claim review lease locks, a unified claim workbench, immutable reviewer notes/action history, SLA-aware prioritization, evidence/FHIR/GraphRAG/agent/guardrail views, request-more-evidence actions, optimistic concurrency checks, human decision reason codes, AI-recommendation override documentation, and realtime review events. Final claim actions remain human-only and flow through the canonical claim-domain state machine.


## Reviewer web application

The `frontend/` application is a Next.js 16 / React 19 human-review dashboard backed by the existing FastAPI authorization and claim-domain controls. It includes a live prioritized queue, claim workbench, evidence/citation explorer, FHIR and GraphRAG views, specialist-agent and guardrail panels, MCP approvals, SLA countdowns, reviewer lease controls, immutable notes, request-more-evidence, and human-only decision operations.

The browser does not store OIDC access tokens in web storage. Next.js acts as a BFF using Authorization Code + PKCE, encrypted HttpOnly session cookies, same-origin mutation enforcement, and an allowlisted backend proxy. Queue and claim updates use reconnectable SSE streams. See `docs/REVIEWER_DASHBOARD_FRONTEND.md`.

## AI operations and observability

MedClaimIQ uses OpenTelemetry for PHI-safe distributed correlation and exposes an internal AI Operations dashboard at `/review/ai-ops` for authorized tenant administrators/auditors. It correlates RAG retrieval telemetry, LangGraph execution paths, model/prompt versions, MCP tool telemetry, evaluation runs, token usage, configurable cost accounting, and SLO breach events. External Phoenix/LangSmith/OTLP export is opt-in; application correctness and auditability remain independent of those vendors.

## Security and privacy engineering

MedClaimIQ uses centralized data classification/DLP, OIDC + tenant RBAC/ABAC + PostgreSQL RLS, KMS/secret-manager boundaries, security headers and abuse limits, approval-first retention/disposition, tamper-evident audit exports, signed supply-chain artifacts, SBOM/SAST/secret/dependency/container/IaC scanning, and release-blocking AI/security quality gates. The repository is intentionally described as **HIPAA-ready**, not HIPAA-certified; production use with PHI requires organization-specific risk analysis, contracts/BAAs, policies, physical/administrative safeguards, and legal review.

## Performance, Scalability and Resilience

MedClaimIQ includes release-blocking performance/resilience contracts, k6 and Locust load suites, Kafka backlog/backpressure modeling, read-only datastore benchmarks, HPA/KEDA verification, controlled staging-only failure injection, Chaos Mesh manifests, capacity planning, baseline-regression gates, and JSON/HTML availability/resilience evidence. Checked-in synthetic results validate the gate logic; production capacity and availability must be measured in a deployment environment that matches production infrastructure and provider quotas.


## Governed AI configuration and experimentation

MedClaimIQ stores model, prompt, retrieval and combined AI runtime settings as immutable tenant-scoped snapshots with canonical SHA-256 hashes. Environment assignments point to approved snapshots, production promotion requires passing evaluation evidence plus independent approval for high-risk changes, and rollback can target only a snapshot previously activated in the same environment. Shadow/A-B/champion-challenger experiments use deterministic privacy-preserving cohort buckets, preserve the human-final-decision boundary, and compare quality, latency and cost without allowing cheaper/faster challengers to hide quality regression. Runtime configuration drift is detected by canonical payload hash. See `docs/AI_CONFIGURATION_EXPERIMENTATION_CHANGE_MANAGEMENT.md`.

## Governed knowledge lifecycle and continuous reindexing

MedClaimIQ governs RAG knowledge as owned sources, logical documents, immutable content versions, independent review/approval, temporally valid releases, quality evidence, and SHA-256 release manifests. PostgreSQL is authoritative for whether a source version is eligible for retrieval; Qdrant is a rebuildable projection. Retrieval applies a PostgreSQL governance check so retired, expired, or future-dated governed versions cannot remain visible while asynchronous vector deletion catches up.

The continuous knowledge worker detects missing/stale embedding projections, performs incremental/full reindexing from authoritative PostgreSQL RAG chunks, supports isolated embedding/index migrations, retries durably, and propagates retirement to Qdrant without deleting audit history. Retrieval-drift checks compare Recall, Precision, NDCG, and no-evidence rate against explicit regression budgets and can block knowledge release promotion. See `docs/KNOWLEDGE_LIFECYCLE_GOVERNANCE.md`.

## Advanced agentic RAG

MedClaimIQ adds a bounded advanced retrieval layer over the governed hybrid RAG foundation. It supports deterministic and optional schema-constrained query rewriting, HyDE-style retrieval passages, allowlisted metadata/self-query filtering, adaptive dense/sparse/hybrid routing, agent-specific retrieval profiles, citation-aware reranking/compression, strict citation enforcement, explicit knowledge-gap detection, and at most one bounded second retrieval pass. Planner/model output may only narrow the already authorized tenant/claim/ACL/time/domain scope, and product safety remains deterministic: PostgreSQL knowledge lifecycle eligibility is authoritative and insufficient evidence routes toward more retrieval, evidence requests, or human review rather than an autonomous claim decision. See `docs/ADVANCED_AGENTIC_RAG.md`.

## Multimodal RAG and cross-modal verification

MedClaimIQ can now fuse governed textual RAG with OCR/layout/table units, image-level evidence, timestamped audio, video transcripts/keyframes, and immutable FHIR snapshots. Every selected item carries a modality-specific citation anchor (page/bbox/timecode/frame/FHIR version), modality-aware reranking preserves source diversity, deterministic amount/code/date cross-checks surface contradictions, and multimodal knowledge-gap logic returns an explicit insufficient-evidence state when required modalities are missing or material conflicts exist. Raw media stays in accepted object storage; multimodal telemetry stores hashes/anchors rather than duplicated image/audio/video bytes. See `docs/MULTIMODAL_RAG.md`.

## Multimodal specialist orchestration

Selected LangGraph specialists now receive profile-bounded multimodal evidence packs with exact citations. Material cross-modal conflicts and missing required modalities trigger deterministic durable human-review checkpoints; agents remain advisory and cannot bypass tenant/ACL or knowledge-governance boundaries.

## Multimodal reviewer investigation

The internal reviewer workbench now includes a dedicated multimodal investigation surface that joins the latest cross-modal evidence pack, multimodal agent investigations, durable human checkpoint context, and exact `mm:*` citations. Reviewers can inspect server-rendered PDF pages with cited bounding boxes highlighted, image evidence, structured invoice/table data, timestamped audio/video evidence, FHIR resource/version snapshots, side-by-side inconsistency evidence, agent-to-evidence traceability, and immutable evidence/finding/checkpoint annotations. Media stays behind the authenticated same-origin BFF with HTTP Range support; raw object-store keys are never sent to browser code. These capabilities remain investigative only—the existing exclusive review lease, optimistic claim version, evidence snapshot, reason codes, override rationale, and human decision endpoint remain the sole final-decision path. See `docs/MULTIMODAL_REVIEWER_WORKBENCH.md`.

## Governed human claim closure

The reviewer decision flow now uses versioned evidence-bound human decision packets with completeness/conflict blocking, AI-vs-human disagreement capture, partial approval, deterministic dual control, locked packet hashes, optimistic concurrency, checkpoint resolution, immutable hash-chained adjudication audit, notification intents, SSE propagation, and evidence-to-human-decision traceability. LLMs, LangGraph, RAG, MCP, and automated workflows remain advisory and cannot independently approve, deny, partially approve, financially execute, or close a claim. See `docs/GOVERNED_HUMAN_CLAIM_CLOSURE.md`.

## Appeal Evidence Reconsideration (cumulative capability)

The post-decision appeal path now re-ingests supplemental document, image, audio, video, and FHIR evidence into an immutable appeal-specific snapshot, performs version-aware original-vs-new comparison and appeal-scoped hybrid retrieval, and exposes a recommendation-only LangGraph workbench for the independently assigned appeal reviewer. Durable checkpoints, citation drill-down, missing-evidence requests, second-level escalation, reviewer annotations, SSE events, and evaluation fixtures preserve complete original-evidence → original-human-decision → supplemental-evidence → AI-assisted-reconsideration → independent-human-resolution lineage. AI/RAG/LangGraph/MCP and automation have no authority to affirm, modify, or overturn a claim decision.

## Controlling-Decision Financial Handoff

The production workflow now continues beyond final human adjudication into a separately governed finance boundary. The newest immutable human decision-history version is bound into a financial authorization packet, line-level payer/member responsibility is reconciled, EOB and X12 835-style artifacts are generated, and a distinct human `finance_approver` must authorize the packet before any positive payment instruction can be staged. Fraud/payment holds, duplicate-payment fingerprints, idempotent adapters, signed settlement status ingestion, reconciliation exceptions, void/reissue dual control, SLA queues, SSE events and hash-chained financial audit provenance are included. AI/LLM, LangGraph, RAG, MCP, workers and adapters have no authority to authorize or execute movement of funds.

## Financial Ledger, ERA/EFT Reconciliation & Accounting Close

The accounting layer extends the human-authorized financial handoff with immutable balanced double-entry journals, multi-record ERA/EFT reference/amount correlation, partial-payment aging, returned-payment reversal entries, independently approved adjustments/recoupments, provider remittance status, and governed accounting-period close. Only a human `accounting_controller` can close a balanced period after reconciliation and exception gates are clear. The background accounting worker may refresh aging metadata only; AI, LangGraph, RAG, MCP, workers, and financial adapters cannot post journals as authority, approve adjustments, close periods, or move funds. See `docs/FINANCIAL_LEDGER_ERA_EFT_ACCOUNTING_CLOSE.md`.

## Financial Analytics, Reserve Adequacy & Payment Integrity Intelligence

The governed finance/accounting stack now exposes a read-only financial intelligence layer for claim reserve history and variance, paid-vs-incurred analytics, leakage/duplicate/overpayment indicators, ERA/EFT anomaly scoring, provider payment-pattern intelligence, recoupment aging, accounting-control exceptions, period-close readiness and portfolio KPIs. A ledger-cited financial RAG/copilot can optionally use the OpenAI Responses API for evidence-bound synthesis; deterministic retrieval and a safe fallback remain available when model assistance is disabled. All derived analytics snapshots are immutable and source-hash bound. AI, LangGraph, RAG, MCP and analytics workers cannot modify governed journals or reserve source-of-truth records, authorize payments, close accounting periods, change adjudication outcomes, or move funds. See `docs/FINANCIAL_ANALYTICS_RESERVE_PAYMENT_INTEGRITY.md`.

## Financial Investigation Case Management & Payment Integrity

Financial intelligence anomalies can now become durable human-owned investigation cases with immutable evidence packs, provider/anomaly clustering, exclusive investigator leases, human root-cause classification, citation-bound annotations, recommendation-vs-human disagreement capture, governed remediation proposals, material second-human approval, payment-hold/void referrals, adjustment/recoupment referrals, SLA queues, SSE events and hash-chained audit provenance. The investigation layer cannot alter adjudication, journals, reserves, payment authorization or move funds.

## Recovery Operations, Provider Disputes & Outcome Verification

Governed remediation referrals now continue into durable recovery cases with immutable evidence packs, exclusive human investigator leases, recoupment/adjustment/hold/void-reissue outcome monitoring, externally evidenced partial and multi-recovery reconciliation, provider-dispute intake, recovery correspondence provenance, material dispute escalation, independent human dispute resolution, recovery aging/SLA queues, SSE updates, remediation-effectiveness analytics, and hash-chained audit traceability through downstream accounting/reconciliation. The recovery worker can create tracking cases only. AI, LangGraph, RAG, MCP, workers and external providers cannot adjudicate disputes, approve accounting changes, authorize payment, collect funds, or move money. See `docs/architecture/ADR-0044-recovery-operations-provider-disputes.md`.

## Provider Dispute Evidence Re-Ingestion & Contract/Policy Decision Support

Provider-submitted dispute evidence now re-enters the governed multimodal pipeline only after the existing accepted-evidence and malware/quarantine boundary has succeeded. Document, image, audio, video and FHIR evidence is version/hash bound into an immutable dispute snapshot together with the original recovery evidence pack and the exact effective provider-agreement/reimbursement-policy versions. The retrieval layer preserves citation anchors, compares original recovery facts with provider evidence, surfaces changed facts and payment-policy contradictions, and produces recommendation-only analysis that stops at a durable independent-human checkpoint. Providers can respond to missing-evidence requests through the portal, while finance reviewers use a citation-driven workbench and SSE progress stream. evidence-bound independent human dispute resolution is the only final resolution path; AI, LangGraph, RAG, MCP and background workers cannot adjudicate disputes, change accounting, authorize payment, collect funds or move money. See `docs/architecture/ADR-0045-provider-dispute-evidence-rag.md`.


## Evidence-Bound Provider Dispute Resolution & Recovery Amendment

Provider disputes now resolve only through a locked human decision packet bound to the immutable evidence/policy snapshot. Mandatory citation/completeness gates, unresolved-policy-conflict blocking, AI-vs-human disagreement rationale, material dual control, immutable recovery-position supersession, accounting/reconciliation reversal referrals and regenerated provider correspondence replace the retired direct resolver. AI, LangGraph, RAG, MCP and workers remain recommendation/support only.

## Recovery Settlement Evidence & Financial Closeout

The amended human-controlled recovery position can now be verified against provider repayment/remittance evidence, multi-installment repayments, recoupment offsets and refund/credit evidence. Finance operators/analysts verify external references and correlate verified recovery to immutable posted ledger journals; partial balances and exceptions remain open. A separate human `finance_approver` must certify financial closeout against a governed accounting period. The recovery-settlement worker only refreshes aging/exception state and cannot verify evidence, post journals, approve accounting, authorize payment, create bank transactions, collect funds or close financially material recovery cases. See `docs/architecture/ADR-047-recovery-settlement-financial-closeout.md`.

## Recovery Settlement Reconciliation Intelligence & Provider Balance Statements

adds a strictly read-only intelligence/reporting projection over the governed recovery-settlement and ledger records. It produces immutable provider balance-statement versions, settlement aging and under/over-recovery analytics, provider recovery history, exception-investigation observations, accounting-period closeout/audit manifests, OpenTelemetry measurements, and settlement/ledger-cited financial RAG. Provider portal statement publication is a separate human-released delivery-provenance record and cannot change a recovery balance. AI, LangGraph, RAG, MCP and background workers cannot alter balances, journals, payment instructions, closeout certificates, bank transactions, collections, or fund movement. See `docs/architecture/ADR-048-recovery-settlement-reconciliation-intelligence.md`.

## Regulatory Predictive Risk Intelligence & Assurance Forecasting

Adds the production supervisory forecasting layer over regulatory remediation portfolios: versioned remediation-failure, deadline-breach, recurrence, and control-deterioration risk signals; governed what-if/stress scenarios; assurance-readiness forecasts; human review; model provenance/evaluation; and strict recommendation-only authority boundaries.


## Regulatory continuous assurance and control drift
The regulatory remediation stack now includes continuous assurance over forecasts: forecast-vs-actual observations, control/remediation drift scoring, evidence freshness surveillance, supervisory early warnings, immutable human investigations, and monitoring-only workers. See `docs/REGULATORY_CONTINUOUS_ASSURANCE_AND_CONTROL_DRIFT.md`.


## Continuous Control Testing and Independent Assurance
See `docs/REGULATORY_CONTINUOUS_CONTROL_TESTING.md` for governed continuous test plans, evidence sampling, exceptions, retests, SoD, and human-only effectiveness conclusions.


## Regulatory Assurance Exceptions & Deficiency Escalation
Adds tenant-safe sample-exception classification, versioned deficiency aggregation, repeated-exception correlation, cross-entity propagation, compensating-control/remediation linkage, enterprise issue and material-weakness *candidate* detection, SLA monitoring, independent human escalation/closure, evaluation, migration 0053, API routes, worker, policy and synthetic scenarios. AI and workers remain recommendation/monitoring-only.


## Enterprise Deficiency Lifecycle ()
Adds governed deficiency investigations, formal human material-weakness/significant-deficiency classification, cross-control/root-cause analysis, executive corrective-action oversight, regulatory commitment linkage, compensating-control expiry monitoring, independent challenge, immutable dispositions and human executive attestations. AI/agents remain recommendation-only.

## Regulatory executive closure governance
The production regulatory remediation stack includes governed executive closure packages, immutable human certifications, post-remediation sustainability assurance, recurrence surveillance, and human-only reopen decisions. AI and background workers are recommendation/monitoring only and cannot certify remediation, accept residual risk, close findings, alter accounting records, or move money.

## Regulatory enterprise knowledge governance
The regulatory remediation stack now includes governed, temporal supervisory knowledge graphs and examination-readiness intelligence with immutable releases and human-only authoritative interpretation approval. See `docs/regulatory/enterprise-knowledge-governance-examination-readiness.md`.


## Regulatory Examination Response Orchestration ()
Live examiner Q&A, evidence refresh, immutable response revisions, human approval, submission receipt reconciliation, follow-up lineage, and SLA escalation with no autonomous regulator transmission.
