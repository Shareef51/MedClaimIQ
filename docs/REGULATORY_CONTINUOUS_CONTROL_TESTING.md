# Production Regulatory Remediation Continuous Control Testing

Release 57 extends continuous assurance into governed continuous control testing, automated evidence sampling, and independent assurance orchestration.

## Traceability
`control -> population -> sample -> evidence -> test -> exception -> retest -> independent human conclusion`

## Production guarantees
- Tenant-scoped plans, runs, samples, and conclusions.
- Versioned test plans and immutable conclusion versions.
- SHA-256 population watermarks and sample-level provenance.
- Deterministic risk-ranked evidence sampling; automation selects evidence but does not determine formal control effectiveness.
- Design-effectiveness, operating-effectiveness, and sustainability test types.
- Cross-entity samples retain entity identity and source evidence.
- Failed/exception samples are aggregated into the human conclusion package.
- Segregation of duties blocks the test preparer from independently concluding the same run.
- Ineffective/inconclusive outcomes can schedule a bounded retest; no worker certifies a control or closes a finding.

## API
- `GET /api/v1/regulatory-control-testing/model`
- `GET /api/v1/regulatory-control-testing/dashboard`
- `POST /api/v1/regulatory-control-testing/plans`
- `POST /api/v1/regulatory-control-testing/runs`
- `POST /api/v1/regulatory-control-testing/samples/{sample_id}/result`
- `GET /api/v1/regulatory-control-testing/runs/{test_run_id}`
- `POST /api/v1/regulatory-control-testing/runs/{test_run_id}/independent-conclusion`

## Reviewer UI contract
### Continuous Control Testing Center
Shows schedules, active test windows, control coverage, sample progress, exceptions, and human conclusion status.

### Evidence Sampling Queue
Shows selected population members, risk scores, selection reason, source watermark, evidence references, test result, and exception state.

### Independent Assurance Review
Shows population/sample provenance, failed samples, evidence chain, SoD state, prior conclusions, and the human-only effectiveness conclusion action.

### Retest Calendar
Shows bounded retests created after ineffective, inconclusive, or exception-bearing conclusions. Retest scheduling never represents remediation approval or control certification.

## SSE event contract
Recommended events: `control_test.plan.created`, `control_test.run.sampled`, `control_test.sample.failed`, `control_test.exception.detected`, `control_test.retest.scheduled`, `control_test.human_conclusion.recorded`.

## Safety boundary
AI, RAG, MCP, agents and workers may orchestrate, sample, retrieve, compare, summarize and recommend. They may not certify controls, approve remediation, accept residual risk, close regulatory findings, alter accounting records, authorize payments, collect funds or move money.
