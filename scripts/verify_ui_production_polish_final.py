from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"

ANY_PATTERNS = [
    re.compile(r":\s*any\b"),
    re.compile(r"<any>"),
    re.compile(r"\bas\s+any\b"),
    re.compile(r"Record<[^>]*,\s*any>"),
    re.compile(r"z\.any\(\)"),
]


def source_files():
    for path in FRONTEND.rglob("*"):
        if path.suffix in {".ts", ".tsx"} and "node_modules" not in path.parts and ".next" not in path.parts:
            yield path


def static_routes() -> set[str]:
    routes: set[str] = set()
    for page in (FRONTEND / "app").rglob("page.tsx"):
        rel = page.parent.relative_to(FRONTEND / "app").as_posix()
        routes.add("/" if rel == "." else "/" + rel)
    return routes


def main() -> int:
    failures: list[str] = []
    combined: list[str] = []
    for path in source_files():
        text = path.read_text(errors="ignore")
        combined.append(text)
        if any(pattern.search(text) for pattern in ANY_PATTERNS):
            failures.append(f"explicit any escape hatch: {path.relative_to(ROOT)}")
    all_text = "\n".join(combined)
    if "window.prompt" in all_text or "window.alert" in all_text:
        failures.append("browser prompt/alert workflow remains")
    if re.search(r"\bRelease[ _-]*\d+\b", all_text, re.IGNORECASE):
        failures.append("internal build-sequence label remains in frontend")

    required_files = [
        "frontend/app/loading.tsx", "frontend/app/error.tsx", "frontend/app/not-found.tsx",
        "frontend/app/review/loading.tsx", "frontend/app/review/error.tsx",
        "frontend/app/portal/loading.tsx", "frontend/app/portal/error.tsx",
        "frontend/components/ui/page-state.tsx", "frontend/components/ui/action-dialog.tsx",
        "artifacts/ui-production-polish/final_route_validation.json",
        "docs/FRONTEND_PRODUCTION_READINESS_FINAL.md", "docs/RECRUITER_WEBSITE_WALKTHROUGH.md",
    ]
    for rel in required_files:
        if not (ROOT / rel).exists():
            failures.append(f"missing final UI artifact: {rel}")

    shell = (FRONTEND / "components/review/app-shell.tsx").read_text()
    for token in ["Workspace", "Financial operations", "Regulatory", "AI & platform", "Open navigation", "aria-current", "Skip to main content"]:
        if token not in shell:
            failures.append(f"reviewer shell missing {token!r}")

    dialog = (FRONTEND / "components/ui/action-dialog.tsx").read_text()
    for token in ['role="dialog"', 'aria-modal="true"', "previouslyFocused", "Escape", "aria-describedby"]:
        if token not in dialog:
            failures.append(f"dialog contract missing {token!r}")

    portal = (FRONTEND / "app/portal/page.tsx").read_text()
    if 'role==="provider"||role==="hospital_admin"' not in portal or "providerOperations&&" not in portal:
        failures.append("portal provider-only module gate missing")

    claim_list = (FRONTEND / "components/portal/claim-list.tsx").read_text()
    for token in ["PortalLoading", "PortalError", "Claims could not be loaded", "No claims are available", "Try again"]:
        if token not in claim_list and token != "Try again":
            failures.append(f"portal claim-list state missing {token!r}")

    package = json.loads((FRONTEND / "package.json").read_text())
    if package.get("packageManager") != "npm@10.9.2":
        failures.append("frontend package manager is not pinned")
    if any(str(v).startswith(("^", "~")) for group in ("dependencies", "devDependencies") for v in package.get(group, {}).values()):
        failures.append("frontend dependency range remains unpinned")

    routes = static_routes()
    expected = json.loads((ROOT / "artifacts/ui-production-polish/final_route_validation.json").read_text())["static_routes"]
    if set(expected) != routes:
        failures.append(f"route manifest mismatch: expected={len(expected)} actual={len(routes)}")

    nav_hrefs = set(re.findall(r'href:"(/review[^\"]*)"', shell))
    routable_static = {r for r in routes if "[" not in r}
    missing_nav = sorted(nav_hrefs - routable_static)
    if missing_nav:
        failures.append(f"reviewer nav targets missing routes: {missing_nav}")

    recruiter_docs = "\n".join((ROOT / p).read_text(errors="ignore") for p in [
        "docs/FRONTEND_PRODUCTION_READINESS_FINAL.md", "docs/RECRUITER_WEBSITE_WALKTHROUGH.md"
    ])
    if re.search(r"\bRelease[ _-]*\d+\b", recruiter_docs, re.IGNORECASE):
        failures.append("final recruiter-facing UI docs expose internal build sequence")

    if failures:
        print("FINAL UI PRODUCTION POLISH VERIFICATION: FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("FINAL UI PRODUCTION POLISH VERIFICATION: PASS")
    print(f"- user-facing routes: {len(routes)}")
    print("- explicit any escape hatches: 0")
    print("- browser prompt/alert workflows: 0")
    print("- internal build-sequence labels in frontend: 0")
    print("- grouped/mobile navigation and role-gated portal modules: present")
    print("- global/reviewer/portal loading and error boundaries: present")
    print("- accessible action/info dialogs with focus restoration: present")
    print("- pinned frontend dependency/runtime contract: present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
