#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
required=[
 'backend/app/domain/advanced_rag.py','backend/app/rag/advanced_query.py','backend/app/rag/agent_retrieval.py',
 'backend/app/rag/advanced_reranking.py','backend/app/rag/citation_enforcement.py','backend/app/rag/knowledge_gap.py',
 'backend/app/services/advanced_rag.py','backend/app/api/v1/advanced_rag.py','backend/app/models/advanced_rag.py',
 'backend/alembic/versions/0026_advanced_agentic_rag.py','sample-data/advanced_rag_eval_v1.json',
 '.github/workflows/advanced-rag-quality-gate.yml','docs/ADVANCED_AGENTIC_RAG.md'
]
missing=[x for x in required if not (ROOT/x).exists()]
if missing: raise SystemExit('missing advanced RAG artifacts: '+', '.join(missing))
policy=json.loads((ROOT/'config/release_engineering_policy.json').read_text())
if 'advanced-rag-quality' not in policy['gates']['required']: raise SystemExit('advanced-rag-quality release gate missing')
main=(ROOT/'backend/app/main.py').read_text()
if '/advanced-rag-model' not in main or 'advanced_rag_router' not in main: raise SystemExit('advanced RAG API not registered/public model missing')
service=(ROOT/'backend/app/services/advanced_rag.py').read_text()
for token in ('scope_preserved','knowledge_governance_filter','strict_citations','max_rounds'):
    if token not in service: raise SystemExit(f'advanced RAG safety contract missing: {token}')
vector=(ROOT/'backend/app/vector/qdrant_store.py').read_text()
if 'scope.source_types' not in vector: raise SystemExit('metadata-aware source_type vector filter missing')
print('advanced RAG architecture verifier: PASS')
