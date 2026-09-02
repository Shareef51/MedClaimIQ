from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"

PATTERNS = {
    "explicit any annotation": re.compile(r":\s*any\b"),
    "generic any": re.compile(r"<any>"),
    "any cast": re.compile(r"\bas\s+any\b"),
    "record any": re.compile(r"Record<[^>]*,\s*any>"),
    "zod any": re.compile(r"z\.any\(\)"),
}


def source_files():
    for path in FRONTEND.rglob("*"):
        if path.suffix in {".ts", ".tsx"} and ".next" not in path.parts and "node_modules" not in path.parts:
            yield path


def main() -> int:
    failures: list[str] = []
    combined = []
    for path in source_files():
        text = path.read_text(errors="ignore")
        combined.append(text)
        for label, pattern in PATTERNS.items():
            if pattern.search(text):
                failures.append(f"{path.relative_to(ROOT)}: {label}")
    all_text = "\n".join(combined)
    if "window.prompt" in all_text or "window.alert" in all_text:
        failures.append("browser prompt/alert workflow remains")
    if re.search(r"\bRelease[ _-]*\d+\b", all_text, re.IGNORECASE):
        failures.append("internal build release label remains in frontend")

    required = {
        FRONTEND / "components/review/app-shell.tsx": ["Financial operations", "Regulatory", "AI & platform", "Open navigation", "aria-current"],
        FRONTEND / "components/ui/action-dialog.tsx": ['role="dialog"', 'aria-modal="true"', "Escape"],
        FRONTEND / "components/review/claim-workbench.tsx": ["Advanced Investigation"],
        FRONTEND / "components/review/operations-dashboard.tsx": ["SLA aging", "RAG quality", "Agent & retrieval latency"],
        FRONTEND / "app/login/page.tsx": ["Synthetic recruiter demo"],
    }
    for path, tokens in required.items():
        text = path.read_text(errors="ignore")
        for token in tokens:
            if token not in text:
                failures.append(f"{path.relative_to(ROOT)} missing {token!r}")

    if failures:
        print("UI PRODUCTION POLISH VERIFICATION: FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("UI PRODUCTION POLISH VERIFICATION: PASS")
    print("- explicit any escape hatches: 0")
    print("- browser prompt/alert workflows: 0")
    print("- internal build release labels in frontend: 0")
    print("- grouped/mobile navigation, accessible dialogs, advanced investigation and dashboards: present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
