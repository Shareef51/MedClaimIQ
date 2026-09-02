# Operational readiness performance execution

Run only against an authorized synthetic/de-identified test environment.

## API load / stress / soak

- `k6 run performance/k6/api_claims.js`
- `k6 run performance/k6/rag_agents_mcp.js`
- `k6 run performance/k6/sse_scale.js`
- `locust -f performance/locust/locustfile.py`

The release evidence must retain target build/version, tenant set, scenario parameters, latency percentiles, throughput, error rate, saturation, cost per case, data-integrity checks and timestamps. Never infer a pass merely because the harness exits successfully.

## Failure and DR exercises

Use the existing Chaos Mesh manifests and DR runbooks with explicit human authorization. Record steady state, injected failure, recovery time, data-integrity proof, tenant-isolation proof and rollback/failback evidence. Production chaos is never launched automatically by the Release 109 worker or certification API.
