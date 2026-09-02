from pathlib import Path
root=Path(__file__).resolve().parents[1]
checks={
 "backend_api":root/"backend/app/api/v1/portal.py",
 "service":root/"backend/app/services/portal.py",
 "migration":root/"backend/alembic/versions/0018_patient_provider_portal.py",
 "frontend":root/"frontend/components/portal/claim-detail.tsx",
 "policy":root/"config/patient_provider_portal_policy.json",
 "docs":root/"docs/PATIENT_PROVIDER_PORTAL.md",
}
missing=[k for k,p in checks.items() if not p.exists()]
if missing: raise SystemExit(f"missing portal artifacts: {missing}")
text=checks["backend_api"].read_text()+checks["service"].read_text()
for required in ["PortalClaimRealtimeStreamer","Permission.EVIDENCE_UPLOAD","privacy_notice","quarantine"]:
    if required not in text: raise SystemExit(f"missing portal contract: {required}")
print("Patient/provider portal architecture verified")
