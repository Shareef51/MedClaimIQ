#!/usr/bin/env python3
from __future__ import annotations
import argparse, ast, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = json.loads((ROOT / "config/release_engineering_policy.json").read_text())


def upgrade_calls(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(), filename=str(path)); calls=[]
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "upgrade":
            for child in ast.walk(node):
                if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
                    if isinstance(child.func.value, ast.Name) and child.func.value.id == "op": calls.append(child.func.attr)
    return calls


def revision(path: Path) -> str:
    m=re.search(r'^revision\s*=\s*["\']([^"\']+)', path.read_text(), re.M)
    return m.group(1) if m else ""


def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument('--from-revision',default=POLICY['migrations'].get('deployed_baseline_example','')); a=ap.parse_args()
    if not a.from_revision: a.from_revision=POLICY['migrations'].get('deployed_baseline_example','')
    paths=sorted((ROOT / "backend/alembic/versions").glob("*.py"))
    revs=[revision(p) for p in paths]
    if a.from_revision:
        if a.from_revision not in revs: raise SystemExit(f'unknown deployed baseline revision: {a.from_revision}')
        paths=paths[revs.index(a.from_revision)+1:]
    blocked=set(POLICY["migrations"]["blocked_upgrade_calls"]); violations=[]
    for path in paths:
        for call in upgrade_calls(path):
            if call in blocked: violations.append({"migration":path.name,"operation":call})
    report={"strategy":"expand-contract","from_revision":a.from_revision or None,"candidate_migrations":[p.name for p in paths],"blocked_operations":sorted(blocked),"violations":violations,"decision":"pass" if not violations else "block"}
    out=ROOT/"artifacts/release/migration-compatibility.json"; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2)); return 0 if not violations else 2

if __name__ == "__main__": raise SystemExit(main())
