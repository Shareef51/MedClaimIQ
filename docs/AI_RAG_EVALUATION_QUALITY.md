# AI/RAG Evaluation & Release Quality

MedClaimIQ treats AI quality as a release-engineering concern. Evaluation uses synthetic/de-identified, versioned golden cases and deterministic metrics wherever a ground-truth label exists. Release decisions never depend solely on an LLM judge.

## Quality suites

- Extraction: field accuracy, OCR token F1, table-cell accuracy.
- Retrieval: Recall@K, Precision@K, MRR and NDCG@K after reranking.
- Citation: exact evidence key/source/version/locator agreement.
- Grounding: groundedness and unsupported-claim rate.
- Security: indirect prompt-injection blocking.
- Specialist agents: structured-output/disposition and evidence-key accuracy.
- Workflow: expected LangGraph route accuracy.
- MCP/tooling: allowlist/deny-policy compliance.
- Human escalation: expected escalation behavior.
- FHIR cross-verification: expected hospital match state.
- Contradictions: detection/severity accuracy.
- Performance: p50/p95 latency and estimated token cost.

## Golden observations

`sample-data/golden_claims_v1.json` is the deterministic CI dataset. `sample-data/adversarial_evaluation_v1.json` contains security and governance regressions. A production test environment may replace the frozen `observed` blocks with observations captured from a deployed candidate; the metric and gate code stays identical.

## Release gate

`config/evaluation_policy.json` contains metric thresholds and maximum baseline-regression budgets. A candidate is blocked when a threshold fails or a baseline regression exceeds its allowed budget. Safety-critical metrics such as prompt-injection resistance and MCP tool-policy compliance have zero regression tolerance.

## Reports and persistence

The CLI writes JSON and standalone HTML reports. Persistent evaluation runs store aggregate/case metrics, configuration hashes and immutable release-gate hashes. Evaluation history is tenant isolated with PostgreSQL RLS. Run, metric, case and gate records are append-only; baselines can be activated/deactivated operationally.

## CI

`.github/workflows/ai-quality-gate.yml` executes backend tests, the golden suite, adversarial suite, all-13-agent suite and retrieval ablation and uploads reports even when a release gate blocks.

## Privacy

Portfolio/demo evaluation data is synthetic/de-identified. Evaluation telemetry should contain labels, scores, token counts and hashes—not PHI, raw production prompts or raw patient evidence.

## Retrieval ablations

`sample-data/retrieval_ablation_v1.json` and `scripts/run_retrieval_ablation.py` compare dense-only, hybrid, and hybrid+reranked retrieval with the same expected evidence IDs. This separates architecture improvements from prompt/model changes.

## Zero-tolerance suites

Security, citation, grounding, MCP tool policy and human-escalation cases are zero-tolerance: one individual failure blocks release even when aggregate metrics are otherwise strong.
