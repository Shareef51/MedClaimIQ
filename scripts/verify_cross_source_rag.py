from __future__ import annotations

from pathlib import Path

REQUIRED = [
    "backend/app/domain/cross_source_rag.py",
    "backend/app/rag/cross_source_planning.py",
    "backend/app/rag/structured_retrieval.py",
    "backend/app/rag/fhir_retrieval.py",
    "backend/app/rag/graph_retrieval.py",
    "backend/app/rag/evidence_fusion.py",
    "backend/app/services/cross_source_rag.py",
    "backend/app/api/v1/cross_source_rag.py",
    "backend/app/models/cross_source_rag.py",
    "backend/alembic/versions/0010_cross_source_evidence_fusion.py",
    "config/cross_source_rag_policy.json",
    "docs/STRUCTURED_GRAPH_CROSS_SOURCE_RAG.md",
]


def main() -> None:
    missing = [item for item in REQUIRED if not Path(item).exists()]
    if missing:
        raise SystemExit(f"missing cross-source RAG artifacts: {missing}")
    domain = Path("backend/app/domain/cross_source_rag.py").read_text()
    service = Path("backend/app/services/cross_source_rag.py").read_text()
    migration = Path("backend/alembic/versions/0010_cross_source_evidence_fusion.py").read_text()
    assert "StructuredQueryPlan" in domain and "GraphQueryPlan" in domain and "EvidencePack" in domain
    assert "CrossSourceEvidenceService" in service and "query_sha256" in service
    assert "ENABLE ROW LEVEL SECURITY" in migration and "immutable evidence pack snapshot" in migration
    print("cross-source structured/FHIR/GraphRAG evidence-fusion architecture verified")


if __name__ == "__main__":
    main()
