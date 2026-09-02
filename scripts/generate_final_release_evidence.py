from pathlib import Path
import json,hashlib
ROOT=Path(__file__).resolve().parents[1]
items=["artifacts/release/final_release_manifest.json","artifacts/release/final_production_readiness_report.json","artifacts/release/final_audit_evidence_index.json"]
out={"release":110,"files":{}}
for rel in items:
    b=(ROOT/rel).read_bytes(); out["files"][rel]=hashlib.sha256(b).hexdigest()
out["bundle_hash"]=hashlib.sha256(json.dumps(out["files"],sort_keys=True).encode()).hexdigest()
p=ROOT/'artifacts/release/final_evidence_bundle.json'; p.write_text(json.dumps(out,indent=2)+"\n"); print(p)
