from __future__ import annotations
from pathlib import Path
import argparse, ast, json, sys
ROOT=Path(__file__).resolve().parents[1]
VERSION_DIR=ROOT/'backend/alembic/versions'

def assignments(path: Path) -> tuple[str|None, object]:
    tree=ast.parse(path.read_text(), filename=str(path))
    values={}
    for node in tree.body:
        name=None; value=None
        if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name):
            name=node.targets[0].id; value=node.value
        elif isinstance(node,ast.AnnAssign) and isinstance(node.target,ast.Name):
            name=node.target.id; value=node.value
        if name in {'revision','down_revision'} and value is not None:
            try: values[name]=ast.literal_eval(value)
            except (ValueError,TypeError): pass
    return values.get('revision'), values.get('down_revision')

def predecessors(value):
    if value is None: return []
    if isinstance(value,str): return [value]
    if isinstance(value,(tuple,list,set)): return list(value)
    return []

entries={}; duplicates=[]
for path in sorted(VERSION_DIR.glob('*.py')):
    if path.name.startswith('__'): continue
    revision, down=assignments(path)
    if not revision: continue
    if revision in entries: duplicates.append(revision)
    entries[revision]={'down_revision':down,'file':path.name}
refs={pred for item in entries.values() for pred in predecessors(item['down_revision'])}
heads=sorted(set(entries)-refs)
roots=sorted(rev for rev,item in entries.items() if not predecessors(item['down_revision']))
missing=sorted({pred for item in entries.values() for pred in predecessors(item['down_revision']) if pred not in entries})
# DFS cycle detection across all historical branches.
state={}; cycles=[]
def visit(rev, stack):
    marker=state.get(rev,0)
    if marker==1:
        try: i=stack.index(rev); cycles.append(stack[i:]+[rev])
        except ValueError: cycles.append([rev,rev])
        return
    if marker==2: return
    state[rev]=1
    for pred in predecessors(entries[rev]['down_revision']):
        if pred in entries: visit(pred,stack+[rev])
    state[rev]=2
for rev in entries: visit(rev,[])
ap=argparse.ArgumentParser(); ap.add_argument('--expected-head', default='0105_final_production_go_live'); args=ap.parse_args()
expected=args.expected_head
result={'revision_count':len(entries),'root_revisions':roots,'heads':heads,'missing_predecessors':missing,'duplicate_revisions':sorted(set(duplicates)),'cycle_count':len(cycles),'expected_head':expected,'migration_chain_integrity_passed':heads==[expected] and not missing and not duplicates and not cycles}
print(json.dumps(result,indent=2))
if not result['migration_chain_integrity_passed']: sys.exit(1)
