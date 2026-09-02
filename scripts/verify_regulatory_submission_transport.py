from pathlib import Path
root=Path(__file__).resolve().parents[1]
domain=(root/'backend/app/domain/regulatory_submission_transport.py').read_text();worker=(root/'backend/app/workers/regulatory_submission_transport.py').read_text();migration=(root/'backend/alembic/versions/0045_regulatory_submission_transport.py').read_text();sse=(root/'backend/app/api/v1/review_workbench.py').read_text()
for token in ['"ai_can_authorize_submission_release": False','"worker_can_authorize_submission_release": False','"worker_can_move_money": False','"human_release_required": True']: assert token in domain
for forbidden in ['release(', 'certify_package(', '_post_journal(', 'authorize_packet(', 'collect_funds(', 'move_money(']: assert forbidden not in worker
assert 'down_revision="0044_recovery_portfolio_control_assurance"' in migration and 'FORCE ROW LEVEL SECURITY' in migration
assert 'regulatory_transport.' in sse
print('regulatory submission transport verifier: PASS')
