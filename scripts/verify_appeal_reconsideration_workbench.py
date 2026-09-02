#!/usr/bin/env python
from __future__ import annotations
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from app.domain.appeal_reconsideration import appeal_reconsideration_contract

required=[
 'backend/app/domain/appeal_reconsideration.py','backend/app/models/appeal_reconsideration.py','backend/app/repositories/appeal_reconsideration.py',
 'backend/app/services/appeal_reconsideration.py','backend/app/schemas/appeal_reconsideration.py','backend/app/api/v1/appeal_reconsideration.py',
 'backend/app/orchestration/appeal_reconsideration.py','backend/alembic/versions/0033_appeal_evidence_reconsideration.py',
 'backend/tests/test_appeal_evidence_reconsideration.py','backend/app/evaluation/appeal_reconsideration.py','backend/tests/test_appeal_reconsideration_evaluation.py','config/appeal_reconsideration_policy.json',
 'sample-data/evaluation/appeal_reconsideration_cases.jsonl','frontend/app/review/appeals/page.tsx',
 'docs/architecture/appeal-evidence-reconsideration.md','.github/workflows/appeal-reconsideration-quality-gate.yml'
]
missing=[x for x in required if not (ROOT/x).exists()]
if missing: raise SystemExit(f'missing Release 38 artifacts: {missing}')

contract=appeal_reconsideration_contract()
authority=contract['authority']
assert authority['authorized_independent_human_required'] is True
for key in ('llm_can_affirm_modify_or_overturn','langgraph_can_affirm_modify_or_overturn','rag_can_affirm_modify_or_overturn','mcp_can_affirm_modify_or_overturn','automation_can_affirm_modify_or_overturn'):
    assert authority[key] is False,key

policy=json.loads((ROOT/'config/appeal_reconsideration_policy.json').read_text())
assert policy['original_decision_immutable'] is True
assert policy['require_independent_human_reviewer'] is True
assert policy['recommendation_agent_adjudication_authority']=='none'
assert set(policy['allowed_reingestion_modalities'])=={'document','image','audio','video','fhir'}
assert policy['require_citation_lineage'] and policy['require_locked_appeal_snapshot']

service=(ROOT/'backend/app/services/appeal_reconsideration.py').read_text()
graph=(ROOT/'backend/app/orchestration/appeal_reconsideration.py').read_text()
for token in ('process_reingestion','build_snapshot','_compare_snapshot','appeal_scoped_hybrid_dense_bm25_reranked','run_reconsideration_agent','resume_checkpoint','request_missing_evidence','escalate','traceability'):
    if token not in service: raise SystemExit(f'missing reconsideration control: {token}')
for token in ('human_appeal_gate','human_appeal_interrupt','authorized_independent_human_appeal_reviewer','adjudication_authority'):
    if token not in graph: raise SystemExit(f'missing LangGraph human gate: {token}')
for forbidden in ('resolve_appeal(','GovernedClosureService(','record_human_decision(','HumanReviewDecisionModel('):
    if forbidden in service or forbidden in graph: raise SystemExit(f'recommendation subsystem crossed adjudication boundary: {forbidden}')

migration=(ROOT/'backend/alembic/versions/0033_appeal_evidence_reconsideration.py').read_text()
for token in ('FORCE ROW LEVEL SECURITY','appeal_evidence_snapshot_payload_immutable','appeal_reconsideration_runs_immutable','appeal_reviewer_annotations_immutable'):
    if token not in migration: raise SystemExit(f'migration governance missing: {token}')

frontend=(ROOT/'frontend/app/review/appeals/page.tsx').read_text()
for token in ('Independent Appeal Review','Recommendation only','Citation drill-down','Second-level escalation'):
    if token not in frontend: raise SystemExit(f'appeal workbench missing: {token}')
bff=(ROOT/'frontend/app/api/reviewer/[...path]/route.ts').read_text()
assert 'reconsideration' in bff

dataset=(ROOT/'sample-data/evaluation/appeal_reconsideration_cases.jsonl').read_text().strip().splitlines()
assert len(dataset)>=5
for line in dataset:
    row=json.loads(line); assert row['requires_human_resolution'] is True
assert {'document','image','audio','video','fhir'} <= {json.loads(x)['modality'] for x in dataset}

release=json.loads((ROOT/'config/release_engineering_policy.json').read_text())
assert 'appeal-reconsideration-quality' in release['gates']['required']
print('appeal evidence re-ingestion/reconsideration workbench verifier: PASS')
