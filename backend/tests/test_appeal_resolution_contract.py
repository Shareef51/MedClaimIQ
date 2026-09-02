from pathlib import Path
from app.domain.appeal_resolution import appeal_resolution_contract

ROOT=Path(__file__).resolve().parents[2]

def test_release39_contract_is_human_only_and_dual_controlled():
    c=appeal_resolution_contract();a=c["authority"];d=c["dual_control"]
    assert not any(a[k] for k in ("llm_can_create_controlling_outcome","langgraph_can_create_controlling_outcome","rag_can_create_controlling_outcome","mcp_can_create_controlling_outcome","automation_can_create_controlling_outcome"))
    assert a["authorized_human_reviewers_required"] and d["overturn"] and d["material_financial_change"] and d["second_reviewer_must_differ"]

def test_release39_migration_has_rls_immutable_tables_and_hash_fields():
    text=(ROOT/"backend/alembic/versions/0034_appeal_resolution_governance.py").read_text()
    for table in ("appeal_decision_packets","appeal_decision_second_reviews","appeal_final_resolutions","appeal_resolution_audit_events"):
        assert table in text
    for marker in ("ENABLE ROW LEVEL SECURITY","FORCE ROW LEVEL SECURITY","reconsideration_snapshot_sha256","packet_locked_sha256","previous_event_sha256","_immutable"):
        assert marker in text

def test_release39_retires_weaker_direct_appeal_resolution_path():
    api=(ROOT/"backend/app/api/v1/post_decision.py").read_text();frontend=(ROOT/"frontend/lib/api.ts").read_text();bff=(ROOT/"frontend/app/api/reviewer/[...path]/route.ts").read_text()
    assert "direct appeal resolution retired" in api and "status_code=410" in api
    assert "resolveAppeal" not in frontend
    assert "(?:assign|reopen|resolve)" not in bff
    assert "resolution(?:" in bff

def test_release39_frontend_exposes_governed_packet_dual_control_and_human_release():
    panel=(ROOT/"frontend/components/review/appeal-resolution-panel.tsx").read_text();api=(ROOT/"frontend/lib/api.ts").read_text();page=(ROOT/"frontend/app/review/appeals/page.tsx").read_text()
    for marker in ("Evidence-bound human resolution","Prepare evidence-bound decision packet","Validate & lock","Second-review approve","Close controlling human resolution","Human release reconsideration notice","human only"):
        assert marker in panel
    for marker in ("saveAppealResolutionPacket","lockAppealResolutionPacket","secondReviewAppealResolution","closeAppealResolution","releaseAppealResolutionNotice"):
        assert marker in api
    assert "AppealResolutionPanel" in page

def test_release39_audit_export_contains_final_resolution_and_audit_chain():
    text=(ROOT/"backend/app/services/communication_delivery.py").read_text()
    assert '"appeal_final_resolutions"' in text and '"appeal_resolution_audit_chain"' in text

def test_no_agent_or_rag_module_imports_final_resolution_service():
    forbidden="AppealResolutionService"
    roots=[ROOT/"backend/app/agents",ROOT/"backend/app/orchestration",ROOT/"backend/app/rag",ROOT/"backend/app/mcp"]
    hits=[]
    for root in roots:
        if not root.exists():continue
        for path in root.rglob("*.py"):
            if forbidden in path.read_text(errors="ignore"):hits.append(str(path.relative_to(ROOT)))
    assert not hits, f"final human appeal resolver imported by automated reasoning/tool modules: {hits}"
