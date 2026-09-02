from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend"


def text(path: str) -> str:
    return (ROOT / path).read_text(errors="ignore")


def test_global_reviewer_and_portal_boundaries_have_loading_error_and_not_found_states():
    required = [
        "frontend/app/loading.tsx",
        "frontend/app/error.tsx",
        "frontend/app/not-found.tsx",
        "frontend/app/review/loading.tsx",
        "frontend/app/review/error.tsx",
        "frontend/app/portal/loading.tsx",
        "frontend/app/portal/error.tsx",
        "frontend/components/ui/page-state.tsx",
    ]
    for path in required:
        assert (ROOT / path).exists(), path
    state = text("frontend/components/ui/page-state.tsx")
    assert 'role="status"' in state
    assert 'role="alert"' in state
    assert "Try again" in state


def test_portal_home_hides_provider_recovery_modules_from_patient_personas():
    page = text("frontend/app/portal/page.tsx")
    assert 'role==="provider"||role==="hospital_admin"' in page
    assert "providerOperations&&" in page
    for component in ["ProviderDisputeCenter", "RecoverySettlementCenter", "ProviderRecoveryBalanceStatements"]:
        assert component in page


def test_portal_claim_list_has_explicit_loading_error_empty_and_retry_states():
    claim_list = text("frontend/components/portal/claim-list.tsx")
    assert "PortalLoading" in claim_list
    assert "PortalError" in claim_list
    assert "Claims could not be loaded" in claim_list
    assert "No claims are available" in claim_list
    assert "retry={()=>void load()}" in claim_list


def test_all_dialog_variants_have_keyboard_focus_and_accessible_description_contracts():
    dialog = text("frontend/components/ui/action-dialog.tsx")
    assert dialog.count('role="dialog"') >= 2
    assert dialog.count('aria-modal="true"') >= 2
    assert "previouslyFocused" in dialog
    assert 'event.key==="Escape"' in dialog or 'event.key === "Escape"' in dialog
    assert 'event.key!=="Tab"' in dialog or 'event.key !== "Tab"' in dialog
    assert "aria-describedby" in dialog


def test_frontend_toolchain_is_pinned_for_reproducible_ci_installation():
    package = json.loads(text("frontend/package.json"))
    assert package["packageManager"] == "npm@10.9.2"
    assert package["engines"]["node"] == ">=22 <23"
    assert package["dependencies"]["next"] == "16.3.1"
    assert package["devDependencies"]["typescript"] == "6.0.3"
    assert all(not str(v).startswith(("^", "~")) for v in package["dependencies"].values())
    assert all(not str(v).startswith(("^", "~")) for v in package["devDependencies"].values())


def test_every_static_reviewer_navigation_destination_exists_as_app_route():
    shell = text("frontend/components/review/app-shell.tsx")
    hrefs = set(re.findall(r'href:"(/review[^\"]*)"', shell))
    routes = set()
    for page in (FRONTEND / "app/review").rglob("page.tsx"):
        rel = page.parent.relative_to(FRONTEND / "app").as_posix()
        if "[" in rel:
            continue
        routes.add("/" + rel)
    assert hrefs
    assert hrefs <= routes


def test_final_recruiter_docs_do_not_expose_internal_build_sequence():
    for path in ["docs/FRONTEND_PRODUCTION_READINESS_FINAL.md", "docs/RECRUITER_WEBSITE_WALKTHROUGH.md"]:
        content = text(path)
        assert not re.search(r"\bRelease[ _-]*\d+\b", content, re.IGNORECASE)
        assert "window.prompt" not in content
        assert "window.alert" not in content
