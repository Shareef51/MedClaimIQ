from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
required = [
    "backend/app/domain/rag.py",
    "backend/app/models/rag.py",
    "backend/app/rag/chunking.py",
    "backend/app/rag/source_builder.py",
    "backend/app/embeddings/openai_provider.py",
    "backend/app/embeddings/batching.py",
    "backend/app/vector/qdrant_store.py",
    "backend/app/services/rag.py",
    "backend/app/workers/rag_indexing.py",
    "backend/alembic/versions/0008_multi_rag_vector_foundation.py",
    "config/multi_rag_policy.json",
    "docs/PRODUCTION_MULTI_RAG_FOUNDATION.md",
]
missing = [item for item in required if not (ROOT / item).exists()]
if missing:
    raise SystemExit(f"missing Multi-RAG artifacts: {missing}")

migration = (ROOT / "backend/alembic/versions/0008_multi_rag_vector_foundation.py").read_text()
for token in ("rag_chunks", "rag_index_jobs", "rag_index_records", "rag_index_dead_letters", "ENABLE ROW LEVEL SECURITY", "FORCE ROW LEVEL SECURITY"):
    if token not in migration:
        raise SystemExit(f"migration contract missing {token}")

qdrant = (ROOT / "backend/app/vector/qdrant_store.py").read_text()
for token in ("tenant_id", "claim_id", "acl_tags", "entity_ids", "create_payload_index", "query_points"):
    if token not in qdrant:
        raise SystemExit(f"Qdrant contract missing {token}")
print("Multi-RAG foundation verification passed")
