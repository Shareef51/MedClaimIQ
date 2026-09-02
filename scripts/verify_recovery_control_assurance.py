from pathlib import Path
root=Path(__file__).resolve().parents[1]
checks={"domain":root/'backend/app/domain/recovery_control_assurance.py',"service":root/'backend/app/services/recovery_control_assurance.py',"worker":root/'backend/app/workers/recovery_control_assurance.py',"migration":root/'backend/alembic/versions/0044_recovery_portfolio_control_assurance.py',"ui":root/'frontend/app/review/recovery-control-assurance/page.tsx',"policy":root/'config/recovery-control-assurance-policy.json',"evaluation":root/'artifacts/recovery-control-assurance/evaluation-dataset.json'}
for name,p in checks.items():
    if not p.exists():raise SystemExit(f"missing {name}: {p}")
domain=checks['domain'].read_text();service=checks['service'].read_text();worker=checks['worker'].read_text();migration=checks['migration'].read_text()
for token in ['"ai_can_certify_regulatory_report": False','"worker_can_certify_or_stage_submission": False','"worker_can_record_external_submission_receipt": False','"automatic_regulatory_submission": False','"automatic_fund_movement": False','"maker_checker_certification_required": True']:
    if token not in domain:raise SystemExit(f"missing Release 49 authority guard: {token}")
for forbidden in ['certify_package(', 'stage_submission(', 'record_submission_receipt(', '_post_journal(', 'authorize_packet(', 'handoff(', 'verify_evidence(', 'decide_certificate(', 'collect_funds(', 'move_money(']:
    if forbidden in worker:raise SystemExit(f"worker authority violation: {forbidden}")
for forbidden in ['_post_journal(', 'authorize_packet(', 'handoff(', 'verify_evidence(', 'decide_certificate(', 'collect_funds(', 'move_money(']:
    if forbidden in service:raise SystemExit(f"control-assurance service financial source mutation violation: {forbidden}")
if 'down_revision="0043_recovery_settlement_reconciliation_intelligence"' not in migration or 'FORCE ROW LEVEL SECURITY' not in migration or 'guard_regulatory_package_locked_fields' not in migration:raise SystemExit('Release 49 migration governance incomplete')
print('recovery portfolio control assurance regulatory submission verifier: PASS')
