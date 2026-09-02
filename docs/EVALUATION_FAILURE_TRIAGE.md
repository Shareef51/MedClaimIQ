# Evaluation failure triage

When a quality gate blocks, do not lower the threshold automatically. The report identifies failed cases, metric thresholds, candidate-vs-baseline deltas and failure reasons.

1. Reproduce the failing case with the exact dataset version and candidate version.
2. Classify the regression: extraction, retrieval, citation, grounding/security, specialist agent, workflow route, MCP tool policy, FHIR verification, contradiction detection, escalation, latency or cost.
3. Compare candidate and baseline observations. For retrieval, run the dense-only/hybrid/hybrid+rereanked ablation before changing prompts.
4. Fix the responsible layer and rerun the same versioned case.
5. Change a golden label or threshold only through an explicit reviewed dataset/policy version change, never simply to make CI green.
6. For zero-tolerance security/governance cases, the release stays blocked until the individual case passes.

Reports intentionally use synthetic/de-identified data. Production failure examples should be minimized/redacted before becoming regression fixtures.
