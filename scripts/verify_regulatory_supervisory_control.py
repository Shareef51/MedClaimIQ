from pathlib import Path
root=Path(__file__).resolve().parents[1]
checks={
 "models":root/'backend/app/models/regulatory_supervisory_control.py',
 "service":root/'backend/app/services/regulatory_supervisory_control.py',
 "api":root/'backend/app/api/v1/regulatory_supervisory_control.py',
 "migration":root/'backend/alembic/versions/0046_regulatory_supervisory_control.py',
 "worker":root/'backend/app/workers/regulatory_supervisory_control.py',
 "ui":root/'frontend/app/review/regulatory-supervision/page.tsx',
 "policy":root/'config/regulatory-supervisory-control-policy.json',
}
for name,path in checks.items():
    assert path.exists(),f"missing {name}: {path}"
service=checks['service'].read_text();worker=checks['worker'].read_text();migration=checks['migration'].read_text()
for token in ['independent_human_supervisory_signoff_required','maker and supervisory checker must be different humans','material regulatory reconciliation exceptions block supervisory certification','cryptographic_acknowledgment','accepted_or_effective_amendment']:
    assert token in service or token in (root/'backend/app/domain/regulatory_supervisory_control.py').read_text(),token
for forbidden in ['certify(', 'release(', 'lease_and_dispatch(', '_post_journal(', 'authorize_packet(', 'collect_funds(', 'move_money(']:assert forbidden not in worker,forbidden
assert 'down_revision="0045_regulatory_submission_transport"' in migration
assert 'FORCE ROW LEVEL SECURITY' in migration
assert 'guard_regulatory_supervisory_certifications_immutable' in migration
print('regulatory supervisory control verifier: PASS')
