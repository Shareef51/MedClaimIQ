# Immutable Release Manifests

Every deployable MedClaimIQ release is represented by one JSON manifest conforming to `schemas/release/release-manifest.schema.json`. A release references API/frontend images only by immutable OCI digest, records the Alembic head, SBOM/provenance hashes, and the result of every mandatory quality gate. Environment GitOps files point to a release ID; they do not reference floating tags such as `latest`.
