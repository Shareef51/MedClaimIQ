from pathlib import Path
root=Path(__file__).resolve().parents[1]
checks={"domain":root/'backend/app/domain/recovery_settlement.py',"models":root/'backend/app/models/recovery_settlement.py',"service":root/'backend/app/services/recovery_settlement.py',"api":root/'backend/app/api/v1/recovery_settlement.py',"worker":root/'backend/app/workers/recovery_settlement.py',"migration":root/'backend/alembic/versions/0042_recovery_settlement_financial_closeout.py',"policy":root/'config/policies/recovery-settlement.yaml',"ui":root/'frontend/app/review/recovery-settlements/page.tsx',"provider_ui":root/'frontend/components/portal/recovery-settlement-center.tsx',"eval":root/'data/evaluation/recovery_settlement.json',"helm":root/'infra/helm/medclaimiq/values.yaml'}
missing=[k for k,p in checks.items() if not p.exists()]
if missing:raise SystemExit(f"missing recovery settlement artifacts: {missing}")
domain=checks['domain'].read_text();service=checks['service'].read_text();worker=checks['worker'].read_text();migration=checks['migration'].read_text();helm=checks['helm'].read_text()
for token in ('"ai_can_collect_funds":False','"background_worker_can_create_bank_transaction":False','"background_worker_can_approve_accounting":False','"background_worker_can_authorize_payment":False','"background_worker_can_close_financial_recovery":False','"independent_human_financial_closeout_required":True'):
    if token not in domain:raise SystemExit(f"authority control missing: {token}")
for forbidden in ('_post_journal(','authorize_packet(','handoff(','collect_funds(','move_money('):
    if forbidden in service or forbidden in worker:raise SystemExit(f"forbidden financial authority call: {forbidden}")
for forbidden in ('verify_evidence(','correlate_ledger(','decide_certificate('):
    if forbidden in worker:raise SystemExit(f"worker must not perform human settlement action: {forbidden}")
if 'down_revision="0041_provider_dispute_resolution_recovery_amendment"' not in migration or 'FORCE ROW LEVEL SECURITY' not in migration or 'protect_verified_recovery_settlement_evidence' not in migration or 'protect_final_recovery_completion_certificate' not in migration:raise SystemExit('migration governance incomplete')
if 'recovery-settlement: {enabled: true' not in helm:raise SystemExit('recovery settlement production worker helm wiring missing')
print('recovery settlement/provider repayment financial closeout verifier: PASS')
