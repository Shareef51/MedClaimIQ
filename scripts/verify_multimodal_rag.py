#!/usr/bin/env python3
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
required=[
 'backend/app/domain/multimodal_rag.py','backend/app/rag/multimodal_routing.py','backend/app/rag/multimodal_fusion.py',
 'backend/app/rag/multimodal_verification.py','backend/app/rag/multimodal_gap.py','backend/app/services/multimodal_rag.py',
 'backend/app/api/v1/multimodal_rag.py','backend/alembic/versions/0027_multimodal_rag.py','sample-data/multimodal_rag_eval_v1.json',
 '.github/workflows/multimodal-rag-quality-gate.yml','docs/MULTIMODAL_RAG.md'
]
missing=[x for x in required if not (ROOT/x).exists()]
if missing: raise SystemExit('missing multimodal artifacts: '+', '.join(missing))
policy=json.loads((ROOT/'config/release_engineering_policy.json').read_text())
if 'multimodal-rag-quality' not in policy['gates']['required']: raise SystemExit('multimodal-rag-quality release gate missing')
main=(ROOT/'backend/app/main.py').read_text()
if 'multimodal_rag_router' not in main or 'multimodal-rag-model' not in main: raise SystemExit('multimodal API not registered/public-model missing')
migration=(ROOT/'backend/alembic/versions/0027_multimodal_rag.py').read_text()
if 'FORCE ROW LEVEL SECURITY' not in migration or 'medclaimiq_reject_immutable_change' not in migration: raise SystemExit('multimodal persistence hardening missing')
print('multimodal RAG verifier: PASS')
