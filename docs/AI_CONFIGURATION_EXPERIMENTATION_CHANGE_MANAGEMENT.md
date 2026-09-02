# AI Configuration Registry, Experimentation and Controlled Change Management

MedClaimIQ treats model, prompt and retrieval settings as governed production artifacts rather than editable environment text.

## Safety boundary

- A configuration snapshot is immutable after creation and contains no credentials or runtime PHI.
- Production promotion requires a linked passing evaluation and an independent approval for high-risk changes.
- Production model, prompt and retrieval changes are high-risk by default.
- The requester cannot self-approve a high-risk production change.
- Rollback changes an environment pointer to a prior immutable snapshot; it never edits history.
- Shadow experiment output is not allowed to drive a claim decision.
- A/B subjects are persisted only as SHA-256 values and deterministic cohort buckets.
- Quality guardrails are authoritative: lower cost or latency cannot compensate for a quality regression beyond policy.

## Configuration model

`ai_configuration_snapshots` stores the exact canonical JSON payload and SHA-256. `ai_environment_assignments` maps a tenant + environment + configuration key to the active snapshot. This supports per-tenant and per-environment overrides without copying mutable prompt text around the deployment.

Recommended configuration keys include:

- `agents.default` — model, fallback model, prompt version and agent role overrides.
- `agents.policy` — a specialist prompt bundle or policy-agent role override.
- `rag.hybrid-retrieval` — fusion, candidate, reranking and confidence settings.
- `rag.embedding` — embedding model/dimension projection metadata.

Secrets remain in KMS/Secrets Manager and must never appear in registry payloads.

## Promotion

1. Create an immutable snapshot.
2. Run the Release 23 evaluation suite against the candidate and record the baseline/run linkage.
3. Request promotion to staging or production.
4. Production requires `evaluation_decision=pass` and `evaluation_run_id`.
5. High-risk changes remain `pending_approval` until another tenant administrator approves.
6. Activation switches the environment assignment pointer atomically.
7. Every action emits a hashed audit event.

## Rollback

Rollback selects an existing snapshot for the same configuration key. The assignment version increments and an immutable `ai.config.rollback.activated` event records the previous and target snapshot IDs plus a hash of the human reason. No automatic claim reprocessing is implied.

## Experiments

Supported modes:

- **shadow** — challenger executes/evaluates but champion remains the user-visible path.
- **ab** — deterministic traffic split.
- **champion_challenger** — governed comparison between active and candidate configurations.

A deterministic bucket is computed from `tenant_id | experiment_id | subject_key`, then the raw subject key is discarded. The persisted assignment contains only `subject_sha256`, bucket, variant and snapshot ID.

Production non-shadow experiments are created in `draft` state and need an independent start approval. This avoids converting “create experiment” into an unreviewed production traffic change.

## Comparison metrics

Experiment observations can link to evaluation runs and trace IDs and record only numerical quality, latency and cost evidence plus an evidence hash. The comparison gate evaluates:

- minimum challenger quality floor;
- maximum quality regression from champion;
- latency regression budget;
- cost regression budget.

Quality failure always blocks, even when cost or latency improves.

## Drift

The active snapshot hash is compared with a canonical JSON hash of the observed runtime configuration. A mismatch generates an immutable drift event. Production release pipelines should treat unresolved production drift as a blocking condition.

## Runtime integration

The specialist-agent runtime resolves `AI_CONFIG_BUNDLE_KEY` through the tenant/environment assignment. A bundle can specify:

```json
{
  "model": "approved-model",
  "fallback_model": "approved-fallback",
  "prompt_version": "2.1.0",
  "role_overrides": {
    "policy": "Approved role instruction text"
  }
}
```

Set `AI_CONFIG_REGISTRY_REQUIRED=true` in controlled production environments after the initial approved assignment has been seeded. This makes a missing registry assignment a startup/execution error instead of silently falling back to static settings.

## Human decision boundary

Experiment routing and configuration promotion change advisory AI behavior only. They do not change MedClaimIQ's core policy that a human reviewer remains the final authority for claim approval/denial.
