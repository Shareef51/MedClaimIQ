#!/usr/bin/env python
from __future__ import annotations
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from app.domain.governed_closure import governed_closure_contract

contract=governed_closure_contract()
assert contract['human_authority']['authenticated_human_reviewer_required'] is True
for key in ('llm_final_decision','langgraph_final_decision','rag_final_decision','mcp_final_decision','automated_financial_adjudication'):
    assert contract['human_authority'][key] is False, key

required=[
    'backend/app/domain/governed_closure.py','backend/app/models/governed_closure.py','backend/app/repositories/governed_closure.py',
    'backend/app/services/governed_closure.py','backend/app/api/v1/governed_closure.py','backend/app/schemas/governed_closure.py',
    'backend/alembic/versions/0030_governed_human_claim_closure.py','frontend/components/review/governed-decision-panel.tsx',
    'config/governed_human_closure_policy.json','docs/GOVERNED_HUMAN_CLAIM_CLOSURE.md',
    'docs/architecture_decisions/ADR-governed-human-claim-closure.md','.github/workflows/governed-human-closure-quality-gate.yml'
]
missing=[p for p in required if not (ROOT/p).exists()]
assert not missing, missing

policy=json.loads((ROOT/'config/governed_human_closure_policy.json').read_text())
assert policy['human_authority']['final_claim_decision_human_only'] is True
assert policy['dual_control']['self_second_review_allowed'] is False
release=json.loads((ROOT/'config/release_engineering_policy.json').read_text())
assert 'governed-human-closure-quality' in release['gates']['required']

service=(ROOT/'backend/app/services/governed_closure.py').read_text()
for marker in ('locked_payload_sha256','evidence_snapshot_sha256','material_graph_conflict','material_multimodal_conflict','required_modality_missing','dual_control_required','resolved_by_human_decision','DecisionNotificationIntentModel'):
    assert marker in service, marker

# No autonomous AI execution layer is allowed to call the canonical final human-decision method.
for relative in ('backend/app/agents','backend/app/rag','backend/app/mcp','backend/app/orchestration','backend/app/workers'):
    for p in (ROOT/relative).rglob('*.py'):
        text=p.read_text()
        assert '.record_human_decision(' not in text, f'autonomous adjudication reference found in {p}'

migration=(ROOT/'backend/alembic/versions/0030_governed_human_claim_closure.py').read_text()
assert 'FORCE ROW LEVEL SECURITY' in migration
assert 'adjudication_audit_events_immutable' in migration
assert 'decision_second_reviews_immutable' in migration
print('governed human claim closure verifier: PASS')
