from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def test_ai_ops_frontend_is_bff_scoped_and_phi_safe():
    route=(ROOT/"frontend/app/api/reviewer/[...path]/route.ts").read_text()
    dash=(ROOT/"frontend/components/llmops/ai-ops-dashboard.tsx").read_text()
    assert "llmops\\/summary" in route
    assert "Raw reviewer queries and retrieved evidence are excluded" in dash
    assert "estimated_cost_usd" in dash

def test_ai_ops_nav_is_admin_or_auditor_only():
    shell=(ROOT/"frontend/components/review/app-shell.tsx").read_text()
    assert '"tenant_admin","auditor"' in shell and "/review/ai-ops" in shell
