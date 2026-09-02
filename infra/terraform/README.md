# Terraform cloud foundations

`aws/` and `azure/` are cloud-ready foundations for private Kubernetes compute plus managed data services. They intentionally keep Qdrant and Redpanda behind endpoint/secret integration boundaries so production can choose a managed vendor or a separately operated cluster without coupling application Terraform state to vendor internals.

Use remote encrypted Terraform state with state locking, separate state per environment, short-lived workload identity in CI, and a reviewed plan before apply. Do not put database passwords or API keys in `.tfvars` committed to source control.

The checked-in Kubernetes baseline is 1.36. Upgrade one minor version at a time after staging compatibility and restore tests.
