from pathlib import Path
root=Path(__file__).resolve().parents[1]
required=['backend/app/domain/regulatory_portfolio_oversight.py','backend/app/models/regulatory_portfolio_oversight.py','backend/app/repositories/regulatory_portfolio_oversight.py','backend/app/services/regulatory_portfolio_oversight.py','backend/app/api/v1/regulatory_portfolio_oversight.py','backend/app/workers/regulatory_portfolio_oversight.py','backend/alembic/versions/0049_regulatory_portfolio_oversight.py','frontend/app/review/regulatory-portfolio-oversight/page.tsx','config/regulatory-portfolio-oversight-policy.json','artifacts/regulatory-portfolio-oversight/evaluation-dataset.json','docs/architecture/regulatory-remediation-portfolio-oversight.md']
missing=[x for x in required if not (root/x).exists()]
if missing:raise SystemExit(f'missing: {missing}')
domain=(root/'backend/app/domain/regulatory_portfolio_oversight.py').read_text();worker=(root/'backend/app/workers/regulatory_portfolio_oversight.py').read_text();migration=(root/'backend/alembic/versions/0049_regulatory_portfolio_oversight.py').read_text();sse=(root/'backend/app/api/v1/review_workbench.py').read_text()
for token in ['"ai_can_certify_controls": False','"worker_can_certify_portfolio": False','"financial_accounting_mutation_authority": False','"fund_movement": False']:assert token in domain
for forbidden in ['certify_portfolio(', 'management_attest(', 'record_test_result(', 'decide_risk_acceptance(', '_post_journal(', 'authorize_packet(', 'collect_funds(', 'move_money(']:assert forbidden not in worker
for token in ['down_revision="0048_regulatory_remediation"','FORCE ROW LEVEL SECURITY','guard_regulatory_portfolio_snapshots_immutable','guard_regulatory_portfolio_certifications_immutable']:assert token in migration
assert 'regulatory_portfolio.' in sse
print('regulatory remediation portfolio oversight verifier: PASS')
