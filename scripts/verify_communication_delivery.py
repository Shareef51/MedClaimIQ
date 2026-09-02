from __future__ import annotations
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
required=[
    "backend/app/domain/communication_delivery.py","backend/app/models/communication_delivery.py",
    "backend/app/repositories/communication_delivery.py","backend/app/services/communication_delivery.py",
    "backend/app/api/v1/communication_delivery.py","backend/app/communications/crypto.py",
    "backend/app/communications/providers.py","backend/app/communications/rendering.py",
    "backend/app/workers/communication_delivery.py","backend/alembic/versions/0032_communication_delivery_compliance.py",
    "config/communication_delivery_policy.json","docs/POST_DECISION_COMMUNICATION_DELIVERY_COMPLIANCE.md",
    "frontend/app/review/communications/page.tsx","backend/tests/test_communication_delivery_compliance.py",
]
missing=[x for x in required if not (ROOT/x).exists()]
if missing: raise SystemExit(f"missing Release 37 artifacts: {missing}")
service=(ROOT/"backend/app/services/communication_delivery.py").read_text()
provider=(ROOT/"backend/app/communications/providers.py").read_text()
domain=(ROOT/"backend/app/domain/communication_delivery.py").read_text()
migration=(ROOT/"backend/alembic/versions/0032_communication_delivery_compliance.py").read_text()
config=(ROOT/"config/communication_delivery_policy.json").read_text()
for token in ["DestinationCipher","queue_released_notice","lease(","verify_webhook_signature","record_receipt","reconcile_notice","render_notice_pdf","build_audit_export","place_legal_hold","recover_dispatch","dashboard","traceability"]:
    if token not in service: raise SystemExit(f"missing delivery control: {token}")
for token in ["EmailDeliveryAdapter","SmsDeliveryAdapter","PortalDeliveryAdapter","ProviderRegistry"]:
    if token not in provider: raise SystemExit(f"missing provider abstraction: {token}")
for token in ["communication_workers_can_adjudicate\": False","providers_can_adjudicate\": False","automation_can_financially_adjudicate\": False"]:
    if token not in domain: raise SystemExit(f"human authority contract missing: {token}")
for token in ["FORCE ROW LEVEL SECURITY","communication_receipts_immutable","communication_reconciliations_immutable","communication_templates_approved_immutable"]:
    if token not in migration: raise SystemExit(f"migration governance missing: {token}")
for token in ['"supported_locales": ["en", "es", "ar"]','"automatic_destructive_purge": false','"workers_can_adjudicate": false']:
    if token not in config: raise SystemExit(f"policy control missing: {token}")
for forbidden in ["resolve_appeal(","GovernedClosureService(","HumanDecision.","record_human_decision"]:
    if forbidden in service or forbidden in provider: raise SystemExit(f"communication subsystem crossed adjudication boundary: {forbidden}")

values=(ROOT/"infra/helm/medclaimiq/values.yaml").read_text()
workers=(ROOT/"infra/helm/medclaimiq/templates/workers.yaml").read_text()
secrets=(ROOT/"infra/helm/medclaimiq/templates/secretproviderclass.yaml").read_text()
for token in ["communication-delivery", "COMMUNICATION_WORKER_LEASE_SECONDS", "communicationDestinationSecretKey"]:
    if token not in values: raise SystemExit(f"production Helm values missing: {token}")
for token in ["COMMUNICATION_DESTINATION_ENCRYPTION_SECRET", "COMMUNICATION_PROVIDER_WEBHOOK_SECRET", "COMMUNICATION_WORKER_TOKEN"]:
    if token not in workers or token not in secrets: raise SystemExit(f"workload secret wiring missing: {token}")
print("post-decision communication delivery/compliance verifier: PASS")
