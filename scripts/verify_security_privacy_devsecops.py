#!/usr/bin/env python3
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
checks={
 'security_policy':ROOT/'config/security_privacy_policy.json','vendor_inventory':ROOT/'config/vendor_security_inventory.json','control_mapping':ROOT/'docs/HIPAA_READY_CONTROL_MAPPING.md','threat_model':ROOT/'docs/SECURITY_THREAT_MODEL.md','incident_runbook':ROOT/'docs/INCIDENT_RESPONSE_RUNBOOK.md','workflow':ROOT/'.github/workflows/security-readiness-gate.yml','migration':ROOT/'backend/alembic/versions/0021_security_privacy_devsecops.py','tests':ROOT/'backend/tests/test_security_privacy_devsecops.py'}
missing=[k for k,p in checks.items() if not p.exists()]
workflow=checks['workflow'].read_text() if checks['workflow'].exists() else ''
required=['gitleaks/gitleaks-action@v3','aquasecurity/trivy-action@v0.36.0','anchore/sbom-action@v0.24.0','sigstore/cosign-installer@v4.0.0']
errors=missing+[x for x in required if x not in workflow]
print(json.dumps({'ok':not errors,'errors':errors},indent=2)); sys.exit(1 if errors else 0)
