# Claim Lifecycle

## Canonical states

```text
submitted
  -> quarantined
  -> extracting
  -> normalizing
  -> verifying
  -> pending_evidence      (optional/repeatable)
  -> ai_reviewed
  -> human_review
  -> completed
```

Additional terminal/supporting states:

- `rejected_at_ingestion`
- `processing_failed`
- `cancelled`
- `appeal_ready`

## Transition rules

- Upload security validation must complete before extraction.
- Extraction failures must be recorded per artifact; they must not disappear from the review surface.
- Verification may fan out into multiple independent checks.
- A claim may enter `pending_evidence` when mandatory evidence is missing.
- `ai_reviewed` means the automated workflow completed; it does not mean the claim is approved or denied.
- Final reviewer action must include actor, timestamp, rationale, and evidence snapshot/version references.

## Idempotency requirement

Every mutating workflow event must carry an idempotency/event identifier so retried delivery cannot duplicate claim transitions, evidence records, notifications, or downstream work.
