#!/usr/bin/env python3
from __future__ import annotations
import argparse
from app.core.config import get_settings
from app.db.session import get_session_factory, set_tenant_context
from app.repositories.knowledge_governance import KnowledgeGovernanceRepository
from app.services.knowledge_governance import KnowledgeGovernanceService


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--actor", default="system:knowledge-drift-scanner")
    args = parser.parse_args()
    settings = get_settings()
    with get_session_factory()() as session:
        set_tenant_context(session, args.tenant_id)
        result = KnowledgeGovernanceService(KnowledgeGovernanceRepository(session, args.tenant_id)).scan_stale_vectors(
            actor=args.actor,
            embedding_model=settings.rag_embedding_model,
            embedding_dimensions=settings.rag_embedding_dimensions,
            index_version=settings.rag_index_version,
        )
        session.commit()
        print(result)
    return 2 if result["count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
