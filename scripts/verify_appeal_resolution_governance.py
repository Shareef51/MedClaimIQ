#!/usr/bin/env python
from __future__ import annotations
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from app.domain.appeal_resolution import appeal_resolution_contract
required=[
'backend/app/domain/appeal_resolution.py','backend/app/models/appeal_resolution.py','backend/app/repositories/appeal_resolution.py','backend/app/services/appeal_resolution.py','backend/app/schemas/appeal_resolution.py','backend/app/api/v1/appeal_resolution.py','backend/alembic/versions/0034_appeal_resolution_governance.py','backend/tests/test_appeal_resolution.py','backend/tests/test_appeal_resolution_contract.py','config/appeal_resolution_policy.json','frontend/components/review/appeal-resolution-panel.tsx','docs/architecture/governed-appeal-resolution.md','artifacts/appeal-resolution/manifest.json','.github/workflows/appeal-resolution-quality-gate.yml']
missing=[x for x in required if not (ROOT/x).exists()]
if missing: raise SystemExit(f'missing Release 39 artifacts: {missing}')
c=appeal_resolution_contract();a=c['authority'];d=c['dual_control'];b=c['blocking_rules']
assert a['authorized_human_reviewers_required'] and not a['automated_financial_execution']
for k in ('llm_can_create_controlling_outcome','langgraph_can_create_controlling_outcome','rag_can_create_controlling_outcome','mcp_can_create_controlling_outcome','automation_can_create_controlling_outcome'): assert a[k] is False,k
assert d['overturn'] and d['material_financial_change'] and d['second_reviewer_must_differ'] and d['original_adjudication_reviewer_excluded']
assert b['locked_snapshot_required'] and b['citations_required'] and b['material_contradictions_must_be_resolved'] and b['open_missing_evidence_blocks']
policy=json.loads((ROOT/'config/appeal_resolution_policy.json').read_text());assert policy['authority']['ai_adjudication_authority']=='none' and policy['authority']['human_only_controlling_outcome']
service=(ROOT/'backend/app/services/appeal_resolution.py').read_text()
for token in ('_validation','unresolved_material_contradictions','open_missing_evidence_requests','recommendation_disagreement_reason_required','dual_control_required','second_review','packet_locked_sha256','appeal_final_resolution','_create_notice','_complete_tasks','traceability'): assert token in service,token
for forbidden_root in ('backend/app/agents','backend/app/orchestration','backend/app/rag','backend/app/mcp'):
    root=ROOT/forbidden_root
    if root.exists():
        for p in root.rglob('*.py'):
            if 'AppealResolutionService' in p.read_text(errors='ignore'): raise SystemExit(f'automated subsystem imported final human resolver: {p.relative_to(ROOT)}')
migration=(ROOT/'backend/alembic/versions/0034_appeal_resolution_governance.py').read_text()
for token in ('FORCE ROW LEVEL SECURITY','appeal_final_resolutions','appeal_resolution_audit_events','packet_locked_sha256','_immutable'): assert token in migration,token
legacy=(ROOT/'backend/app/api/v1/post_decision.py').read_text();assert 'direct appeal resolution retired' in legacy and 'status_code=410' in legacy
bff=(ROOT/'frontend/app/api/reviewer/[...path]/route.ts').read_text();assert '(?:assign|reopen|resolve)' not in bff and '/resolution' in bff
transport=(ROOT/'backend/app/services/communication_delivery.py').read_text();assert 'appeal_final_resolutions' in transport and 'appeal_resolution_audit_chain' in transport
release=json.loads((ROOT/'config/release_engineering_policy.json').read_text());assert 'appeal-resolution-quality' in release['gates']['required']
print('evidence-bound dual-control appeal resolution verifier: PASS')
