from pathlib import Path
root=Path(__file__).resolve().parents[1]
required=[
 'backend/app/domain/regulatory_examination.py','backend/app/models/regulatory_examination.py','backend/app/repositories/regulatory_examination.py','backend/app/services/regulatory_examination.py','backend/app/api/v1/regulatory_examination.py','backend/app/workers/regulatory_examination.py','backend/alembic/versions/0047_regulatory_examination.py','frontend/app/review/regulatory-examinations/page.tsx','config/regulatory-examination-policy.json','artifacts/regulatory-examination/evaluation-dataset.json'
]
missing=[x for x in required if not (root/x).exists()]
assert not missing,missing
service=(root/'backend/app/services/regulatory_examination.py').read_text();worker=(root/'backend/app/workers/regulatory_examination.py').read_text();domain=(root/'backend/app/domain/regulatory_examination.py').read_text();migration=(root/'backend/alembic/versions/0047_regulatory_examination.py').read_text();sse=(root/'backend/app/api/v1/review_workbench.py').read_text()
for token in ['build_evidence_pack','search_evidence','draft_response','approve_response','deliver_response','record_finding','add_commitment','close_examination','previous_response_sha256','source_watermark_sha256']:assert token in service,token
for forbidden in ['approve_response(', 'deliver_response(', '_post_journal(', 'authorize_packet(', 'collect_funds(', 'move_money(']:assert forbidden not in worker,forbidden
for token in ['"ai_can_approve_examination_response": False','"worker_can_represent_human_regulatory_authority": False','human_maker_checker_response_governance_required']:assert token in domain,token
for token in ['FORCE ROW LEVEL SECURITY','guard_regulatory_examination_evidence_packs_immutable','guard_regulatory_examination_responses_finalized_immutable']:assert token in migration,token
assert 'regulatory_examination.' in sse
print('regulatory examination/inquiry response verifier: PASS')
