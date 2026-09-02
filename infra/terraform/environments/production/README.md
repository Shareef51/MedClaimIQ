# Production environment
Use a dedicated cloud account/subscription with three availability zones, private data services, production WAF/TLS, remote state with locking, immutable signed images, and `helm upgrade --install --atomic --wait` using `values-production.yaml`. Promotion must follow staging quality/security/infrastructure gates.
