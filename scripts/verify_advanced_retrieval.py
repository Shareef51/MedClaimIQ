from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
required = [
    "backend/app/sparse/provider.py",
    "backend/app/rag/query_intelligence.py",
    "backend/app/rag/fusion.py",
    "backend/app/rag/reranking.py",
    "backend/app/rag/compression.py",
    "backend/app/rag/assessment.py",
    "backend/app/rag/telemetry.py",
    "backend/alembic/versions/0009_advanced_hybrid_retrieval.py",
    "config/advanced_retrieval_policy.json",
    "docs/ADVANCED_HYBRID_MULTI_RAG_RETRIEVAL.md",
    "docs/architecture_decisions/ADR-011-hybrid-retrieval-and-no-evidence.md",
]
missing = [item for item in required if not (ROOT / item).exists()]
if missing:
    raise SystemExit(f"missing advanced retrieval artifacts: {missing}")

qdrant = (ROOT / "backend/app/vector/qdrant_store.py").read_text()
for token in ("sparse_vectors_config", "Modifier.IDF", 'DENSE_VECTOR_NAME = "dense"', 'SPARSE_VECTOR_NAME = "sparse"', "minimum_authority_rank"):
    if token not in qdrant:
        raise SystemExit(f"hybrid Qdrant contract missing {token}")

service = (ROOT / "backend/app/services/rag.py").read_text()
for token in ("HybridRetrievalService", "reciprocal_rank_fusion", "assess_retrieval", "explicit_no_evidence", "expanded_to_all_authorized_domains"):
    if token not in service:
        raise SystemExit(f"advanced retrieval service missing {token}")

migration = (ROOT / "backend/alembic/versions/0009_advanced_hybrid_retrieval.py").read_text()
for token in ("rag_retrieval_runs", "rag_retrieval_candidates", "ENABLE ROW LEVEL SECURITY", "FORCE ROW LEVEL SECURITY", "query_sha256", "append-only retrieval telemetry"):
    if token not in migration:
        raise SystemExit(f"advanced retrieval migration missing {token}")
if "raw_query" in migration:
    raise SystemExit("raw query persistence must not be introduced into retrieval telemetry")

print("Advanced hybrid retrieval verification passed")
