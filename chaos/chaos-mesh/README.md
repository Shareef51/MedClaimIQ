# MedClaimIQ Chaos Mesh experiments

These manifests are **staging-first** failure-injection templates. They are intentionally not installed by the normal production Helm release.

Rules:
- synthetic/de-identified claims only;
- prove steady state before injection;
- production execution requires an explicit approved change and an isolated blast radius;
- abort immediately if authorization, tenant isolation, human-decision boundaries, or evidence integrity degrade;
- experiments must complete inside the policy maximum duration;
- collect OpenTelemetry, Kafka lag, API error rate, SLO and database evidence before/after.

The reference manifests use Chaos Mesh `chaos-mesh.org/v1alpha1` APIs and are intended for the current 2.8.x controller generation.
