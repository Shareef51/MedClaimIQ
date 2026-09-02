from pathlib import Path
root=Path(__file__).resolve().parents[1]
checks={
 "domain":root/"backend/app/domain/provider_dispute_resolution.py",
 "models":root/"backend/app/models/provider_dispute_resolution.py",
 "service":root/"backend/app/services/provider_dispute_resolution.py",
 "api":root/"backend/app/api/v1/provider_dispute_resolution.py",
 "migration":root/"backend/alembic/versions/0041_provider_dispute_resolution_recovery_amendment.py",
 "policy":root/"config/policies/provider-dispute-resolution.yaml",
 "ui":root/"frontend/app/review/provider-disputes/page.tsx",
 "eval":root/"data/evaluation/provider_dispute_resolution.json",
}
missing=[k for k,p in checks.items() if not p.exists()]
if missing:raise SystemExit(f"missing provider dispute resolution artifacts: {missing}")
domain=checks["domain"].read_text();service=checks["service"].read_text();migration=checks["migration"].read_text();old=(root/"backend/app/services/recovery_operations.py").read_text()
for token in ('"ai_can_resolve_dispute":False','"background_worker_can_change_accounting":False','"background_worker_can_authorize_payment":False','"background_worker_can_collect_funds":False','"background_worker_can_move_money":False','"material_dispute_dual_control_required":True'):
    if token not in domain:raise SystemExit(f"authority control missing: {token}")
for forbidden in ("_post_journal(","authorize_packet(","handoff(","collect_funds(","move_money("):
    if forbidden in service:raise SystemExit(f"forbidden money/accounting call in resolution service: {forbidden}")
if "direct provider dispute resolution is retired" not in old:raise SystemExit("legacy direct resolver is not retired")
if 'down_revision="0040_provider_dispute_intelligence"' not in migration or "FORCE ROW LEVEL SECURITY" not in migration:raise SystemExit("migration governance incomplete")
print("provider dispute resolution/recovery amendment verifier: PASS")
