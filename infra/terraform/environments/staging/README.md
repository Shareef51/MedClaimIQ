# Staging environment
Use a distinct cloud account/subscription, remote state, DNS zone, KMS/Key Vault keys and workload identity. Apply the cloud module, install cluster prerequisites, then deploy `infra/helm/medclaimiq` with `values-staging.yaml`.
