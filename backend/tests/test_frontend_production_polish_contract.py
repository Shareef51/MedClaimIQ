from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend"


def _frontend_text() -> str:
    parts: list[str] = []
    for path in FRONTEND.rglob("*"):
        if path.suffix in {".ts", ".tsx", ".css"} and ".next" not in path.parts:
            parts.append(path.read_text(errors="ignore"))
    return "\n".join(parts)


def test_finished_frontend_has_no_build_release_labels_or_browser_prompt_workflows():
    text = _frontend_text()
    assert not re.search(r"\bRelease[ _-]*\d+\b", text, re.IGNORECASE)
    assert "window.prompt" not in text
    assert "window.alert" not in text
    assert not re.search(r"\bprompt\s*\(", text)
    assert not re.search(r"\balert\s*\(", text)


def test_reviewer_navigation_is_grouped_responsive_and_accessible():
    shell = (FRONTEND / "components/review/app-shell.tsx").read_text()
    for token in ["Workspace", "Financial operations", "Regulatory", "AI & platform", "aria-current", "Open navigation", "Skip to main content", "lg:pl-72"]:
        assert token in shell
    assert "mobileOpen" in shell and "Reviewer navigation" in shell


def test_regulatory_actions_use_accessible_dialogs_and_typed_contracts():
    dialog = (FRONTEND / "components/ui/action-dialog.tsx").read_text()
    assert 'role="dialog"' in dialog and 'aria-modal="true"' in dialog
    regulatory_pages = "\n".join(p.read_text() for p in (FRONTEND / "app/review").glob("regulatory*/page.tsx"))
    assert "ActionDialog" in regulatory_pages
    assert not re.search(r"\bany\b", regulatory_pages)
    schemas = (FRONTEND / "lib/regulatory-schemas.ts").read_text()
    assert "regulatoryExaminationDashboardSchema" in schemas
    assert "regulatoryTransportDashboardSchema" in schemas
    assert "portfolioSnapshotSchema" in schemas
    assert not re.search(r"\bany\b", schemas)


def test_examination_readiness_and_commitments_are_live_workbenches():
    readiness = (FRONTEND / "app/review/regulatory-examination-readiness/page.tsx").read_text()
    commitments = (FRONTEND / "app/review/regulatory-examination-commitments/page.tsx").read_text()
    for token in ["regulatoryExaminationDashboard", "regulatoryRemediationDashboard", "regulatoryPortfolioDashboard", "Readiness by inquiry"]:
        assert token in readiness
    for token in ["regulatoryExaminationDashboard", "regulatoryExaminationTraceability", "Commitment register"]:
        assert token in commitments
    assert "Live supervisory metric" not in readiness + commitments


def test_synthetic_persona_login_is_non_production_only():
    login = (FRONTEND / "app/login/page.tsx").read_text()
    route = (FRONTEND / "app/api/auth/demo/route.ts").read_text()
    env = (FRONTEND / "lib/server/env.ts").read_text()
    assert "Synthetic recruiter demo" in login
    assert 'process.env.NODE_ENV !== "production"' in env
    assert "allowDemoSession" in route and "Synthetic demo login is disabled" in route
    for role in ["claims_reviewer", "tenant_admin", "auditor", "finance_analyst", "provider", "patient"]:
        assert role in login + route


def test_technical_retrieval_views_are_grouped_under_advanced_investigation():
    workbench = (FRONTEND / "components/review/claim-workbench.tsx").read_text()
    assert "Advanced Investigation" in workbench
    assert "Clinical verification" in workbench
    assert "Evidence relationships" in workbench
    assert "AI orchestration" in workbench
    tabs_block = workbench.split("const tabs", 1)[-1].split("];", 1)[0]
    assert 'FHIR' not in tabs_block
    assert 'GraphRAG' not in tabs_block
    assert 'Agents' not in tabs_block


def test_portal_has_theme_boundary_and_explicit_operation_states():
    shell = (FRONTEND / "components/portal/portal-shell.tsx").read_text()
    css = (FRONTEND / "app/globals.css").read_text()
    assert "portal-theme" in shell and ".portal-theme" in css
    for name in ["provider-dispute-center.tsx", "provider-recovery-balance-statements.tsx", "recovery-settlement-center.tsx"]:
        text = (FRONTEND / "components/portal" / name).read_text()
        assert "Loading" in text
        assert "role=\"alert\"" in text or 'role="alert"' in text
        assert "return null" not in text


def test_accessibility_and_mobile_contracts_are_present():
    queue = (FRONTEND / "components/review/review-queue.tsx").read_text()
    dialog = (FRONTEND / "components/ui/action-dialog.tsx").read_text()
    assert "review-queue-search" in queue and "<caption" in queue and 'role="alert"' in queue
    assert "Escape" in dialog and "event.key !== \"Tab\"" in dialog
    css = (FRONTEND / "app/globals.css").read_text()
    assert "prefers-reduced-motion" in css and ".sr-only" in css


def test_operations_dashboard_surfaces_meaningful_live_metrics():
    dash = (FRONTEND / "components/review/operations-dashboard.tsx").read_text()
    for token in ["Claim volume & risk", "SLA aging", "Recovery trend & progress", "Regulatory exposure", "RAG quality", "Agent & retrieval latency"]:
        assert token in dash
    for api in ["reviewerApi.queue", "reviewerApi.llmopsSummary", "reviewerApi.recoveryOperationsPortfolio", "reviewerApi.regulatoryExaminationDashboard"]:
        assert api in dash


def test_recruiter_facing_materials_hide_internal_build_sequence():
    files = [
        ROOT / "README.md",
        ROOT / "docs/RECRUITER_DEMO_GUIDE.md",
        ROOT / "docs/FINAL_PROJECT_BUILD_SUMMARY.md",
        ROOT / "docs/FINAL_GO_LIVE_CHECKLIST.md",
        ROOT / "docs/FINAL_PRODUCTION_GO_LIVE.md",
        ROOT / "docs/FINAL_PRODUCTION_READINESS_REPORT.md",
    ]
    text = "\n".join(p.read_text() for p in files)
    assert not re.search(r"\bRelease[ _-]*\d+\b", text, re.IGNORECASE)
    assert "/108/109/110" not in text


def test_frontend_types_are_explicit_without_any_escape_hatches():
    offenders: list[str] = []
    patterns = [
        re.compile(r":\s*any\b"),
        re.compile(r"<any>"),
        re.compile(r"\bas\s+any\b"),
        re.compile(r"Record<[^>]*,\s*any>"),
        re.compile(r"z\.any\(\)"),
    ]
    for path in FRONTEND.rglob("*"):
        if path.suffix not in {".ts", ".tsx"} or ".next" in path.parts:
            continue
        text = path.read_text(errors="ignore")
        if any(pattern.search(text) for pattern in patterns):
            offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []
