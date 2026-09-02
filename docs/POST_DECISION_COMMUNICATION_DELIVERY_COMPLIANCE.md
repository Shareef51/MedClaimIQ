# Production Post-Decision Communication Delivery, Regulatory Compliance & Operational Reconciliation

## Purpose

This layer transports **human-released** adjudication notices after the governed closure and appeals workflow. It is deliberately downstream of adjudication. A communication worker, transport provider, webhook, retry policy, template renderer, reconciliation job, or AI component cannot create, approve, deny, modify, overturn, reopen, settle, or financially adjudicate a claim.

## End-to-end control flow

`locked evidence -> locked human decision -> human-released notice -> approved template version -> consent/destination resolution -> encrypted dispatch -> worker lease -> provider -> signed receipt -> reconciliation -> appeal lifecycle`

The source decision ID, evidence snapshot hash, notice payload hash, template content hash, dispatch payload hash, provider event hash and decision-history hashes remain independently traceable.

## Provider abstraction

The transport control plane exposes `CommunicationProvider` and three channel adapters:

- email
- SMS
- authenticated portal inbox

Sandbox adapters are the local/default implementation. Production adapters implement the same contract and obtain credentials from workload secret stores. Provider responses can alter only transport state.

## Encrypted destinations

Email addresses, phone numbers and portal destinations are stored as AES-GCM ciphertext with a key version and HMAC fingerprint. API responses return the fingerprint, never plaintext or ciphertext. Decryption occurs only inside the delivery worker immediately before provider dispatch. Production deployments must source the encryption secret from KMS/secret manager and rotate `COMMUNICATION_DESTINATION_KEY_VERSION` under a managed migration.

## Consent and preferences

Endpoints carry channel, locale, consent status and accessibility preferences. Marketing-style opt-out does not silently erase required regulatory communication; the authenticated portal remains the required fallback channel. Direct email/SMS dispatch is suppressed when the endpoint is opted out.

## Template governance

Communication templates are versioned by key, semantic version, locale and channel. New versions start as `draft`. Approval requires a second authorized human reviewer, and approved versions are immutable at the database layer. Release 37 ships deterministic English, Spanish and Arabic baseline wording that can be provisioned only through this two-person approval flow.

## Accessibility-ready artifacts

Each deterministic notice rendering produces:

- plain text
- semantic HTML with article/section/headings
- explicit language metadata
- a text-layer PDF suitable for archival and downstream accessibility validation

The configured target is WCAG 2.2 AA. A production release should include organization-specific PDF/UA validation if PDF/UA conformance is contractually required.

## Worker leasing and idempotency

Dispatches are unique by tenant and idempotency key. Workers claim eligible rows with an expiring lease and may execute only a dispatch leased to their worker ID. The worker revalidates all of the following immediately before sending:

1. the notice exists and has a human release timestamp;
2. the notice is not a draft;
3. the endpoint remains active;
4. the referenced template is human-approved;
5. the rendered payload hash is unchanged.

Leases expire so another worker can safely recover abandoned work.

## Retry, bounce and DLQ behavior

Retryable provider rejections use exponential backoff bounded by `COMMUNICATION_RETRY_MAX_SECONDS`. Terminal failures are dead-lettered and create an operational incident. Signed provider receipts can transition a sent message to delivered, bounced, complaint, failed or retry-pending. Provider event IDs are unique for idempotent webhook replay handling.

## Signed provider receipts

Provider webhooks are HMAC-SHA256 verified before tenant-scoped state is loaded. Every accepted receipt stores:

- provider event ID
- provider message ID
- status
- receipt payload SHA-256
- signature verification result
- provider occurrence time
- local receipt time

Receipt rows are immutable.

## Regulatory deadline controls

Each dispatch receives a deadline derived from the human notice release timestamp and the configured regulatory delivery interval. Dashboards and reconciliation surface deadline breaches. Transport deadlines never alter adjudication outcomes.

## Reconciliation

Reconciliation compares the released notice, expected dispatches, confirmed provider receipts and correspondence provenance. It records an immutable reconciliation hash and gaps such as:

- no dispatch generated
- no confirmed delivery
- regulatory delivery deadline breached

At least one confirmed required-channel delivery can mark the communication intent delivered. The original claim decision remains untouched.

## Correspondence provenance

Accepted outbound provider submissions and inbound provider receipts are written to the existing append-only external correspondence ledger using hashes and external message IDs. Destinations are not copied into the correspondence ledger.

## Retention and legal hold

Communication retention defaults to 2,555 days and is configurable. Destructive automated purge is disabled. A human reviewer can place/release a legal hold; an active hold always blocks disposition eligibility. The retention API is evaluative and never deletes evidence or correspondence.

## Audit export

The audit export ZIP contains a signed JSON manifest and released notice PDFs. The manifest includes decision-history hashes, evidence-bound notice hashes, dispatches, receipts, correspondence and retention status. It excludes destination plaintext/ciphertext. The manifest is SHA-256 hashed and HMAC signed.

## Observability and SLOs

Dispatch execution creates OpenTelemetry spans with non-PHI identifiers and transport dimensions. The operational dashboard exposes queue depth, sent/waiting receipt, delivered, bounced, dead-lettered, deadline breaches, open incidents and on-time delivery SLO percentage. The default target is 99%.

## Incident recovery

Terminal transport failures require an authorized human operations reviewer to requeue the dispatch with a documented recovery reason. Recovery changes only transport state and closes related transport incidents.

## Security and authority boundary

The communication subsystem intentionally does not import or invoke the canonical human adjudication service. The following have **zero** adjudication authority:

- email/SMS/portal providers
- delivery workers
- provider webhooks
- retry/DLQ automation
- template rendering
- reconciliation
- OpenAI/LLM output
- LangGraph agents
- RAG
- MCP tools

Only the existing authenticated human-review workflows can record or reconsider adjudication outcomes.
