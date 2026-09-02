#!/usr/bin/env python
from __future__ import annotations
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from app.domain.post_decision import post_decision_contract

contract=post_decision_contract(); authority=contract['human_authority']
assert authority['ai_may_draft_or_summarize'] is True
assert authority['authorized_human_required_for_notice_release'] is True
assert authority['independent_authorized_human_required_for_appeal_resolution'] is True
for key in ('llm_may_issue_or_overturn','langgraph_may_issue_or_overturn','rag_may_issue_or_overturn','mcp_may_issue_or_overturn','automation_may_issue_or_overturn','automated_financial_execution'):
    assert authority[key] is False,key

required=[
    'backend/app/domain/post_decision.py','backend/app/models/post_decision.py','backend/app/repositories/post_decision.py','backend/app/services/post_decision.py','backend/app/api/v1/post_decision.py','backend/app/schemas/post_decision.py',
    'backend/alembic/versions/0031_post_decision_communications_appeals.py','config/post_decision_communications_policy.json','frontend/components/review/post-decision-operations.tsx',
    'docs/POST_DECISION_COMMUNICATIONS_APPEALS.md','docs/architecture_decisions/ADR-post-decision-communications-appeals.md','.github/workflows/post-decision-appeals-quality-gate.yml'
]
missing=[x for x in required if not (ROOT/x).exists()]; assert not missing,missing
policy=json.loads((ROOT/'config/post_decision_communications_policy.json').read_text())
assert policy['governance']['notice_release_requires_authorized_human'] is True
assert policy['governance']['appeal_resolution_requires_independent_human_reviewer'] is True
assert policy['governance']['original_decision_records_are_immutable'] is True
assert policy['governance']['ai_can_overturn_decision'] is False
assert policy['max_delivery_attempts']>=1
release=json.loads((ROOT/'config/release_engineering_policy.json').read_text())
assert 'post-decision-appeals-quality' in release['gates']['required']

service=(ROOT/'backend/app/services/post_decision.py').read_text()
for marker in ('locked_decision_payload_sha256','evidence_snapshot_sha256','AppealStatus.LATE_PENDING_REVIEW','independent from original adjudication reviewers','previous_version_sha256','dead_lettered','automated_financial_execution','direct appeal resolution retired'):
    assert marker in service,marker

# Automated AI execution layers may not invoke the human-only post-decision authority methods.
for relative in ('backend/app/agents','backend/app/rag','backend/app/mcp','backend/app/orchestration','backend/app/workers'):
    for p in (ROOT/relative).rglob('*.py'):
        text=p.read_text()
        for forbidden in ('.release_notice(','.reopen_appeal(','.resolve_appeal(','.record_human_decision('):
            assert forbidden not in text,f'autonomous human-authority call {forbidden} found in {p}'

migration=(ROOT/'backend/alembic/versions/0031_post_decision_communications_appeals.py').read_text()
assert 'FORCE ROW LEVEL SECURITY' in migration
for marker in ('decision_history_versions_immutable','appeal_resolutions_immutable','appeal_review_assignments_immutable','communication_dead_letters_immutable'):
    assert marker in migration,marker
stream=(ROOT/'backend/app/realtime/streaming.py').read_text()
assert '"appeal."' in stream and '"communication."' in stream
print('post-decision communications and appeals verifier: PASS')
