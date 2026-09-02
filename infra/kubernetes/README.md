# Kubernetes bootstrap

Create the `medclaimiq` namespace before Helm installation. The namespace enforces the Kubernetes `restricted` Pod Security Standard. Install a supported ingress controller, metrics-server, Secrets Store CSI driver plus the selected cloud provider, and optionally KEDA/cert-manager before installing the chart.

Production installation should use immutable image digests and `helm upgrade --install --atomic --wait`.
