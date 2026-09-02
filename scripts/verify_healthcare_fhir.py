from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
required=[
    'backend/app/domain/fhir.py','backend/app/fhir/gateway.py','backend/app/fhir/smart.py','backend/app/fhir/identity.py',
    'backend/app/fhir/verification.py','backend/app/fhir_canonical.py','backend/app/models/fhir.py','backend/app/services/fhir.py',
    'backend/app/api/v1/fhir.py','backend/app/workers/fhir_sync.py','backend/alembic/versions/0006_healthcare_fhir.py','sample-data/fhir_synthetic_bundle.json',
    'config/healthcare_fhir_policy.json','docs/HEALTHCARE_FHIR_INTEGRATION.md'
]
missing=[p for p in required if not (ROOT/p).exists()]
if missing: raise SystemExit(f'Missing FHIR architecture files: {missing}')
text=(ROOT/'backend/alembic/versions/0006_healthcare_fhir.py').read_text()
for token in ('fhir_resource_snapshots','patient_identity_matches','hospital_cross_verifications','healthcare_event_outbox','ENABLE ROW LEVEL SECURITY','FORCE ROW LEVEL SECURITY'):
    if token not in text: raise SystemExit(f'Missing migration contract: {token}')
print('Healthcare FHIR architecture verification passed')
