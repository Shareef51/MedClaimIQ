#!/usr/bin/env python3
"""Process persisted knowledge reindex jobs for one tenant.

Production usage is intended from a Kubernetes CronJob/worker with workload identity and
normal MedClaimIQ DB/Redis/Qdrant/OpenAI configuration. The database is the queue authority.
"""
from __future__ import annotations

import argparse
from app.core.config import get_settings
from app.core.rag_factory import build_cached_embedder, build_vector_store
from app.db.session import get_session_factory, set_tenant_context
from app.repositories.knowledge_governance import KnowledgeGovernanceRepository
from app.repositories.rag import RAGRepository
from app.workers.knowledge_reindex import KnowledgeReindexWorker


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--limit", type=int, default=25)
    args = parser.parse_args()
    settings = get_settings()
    with get_session_factory()() as session:
        set_tenant_context(session, args.tenant_id)
        governance = KnowledgeGovernanceRepository(session, args.tenant_id)
        worker = KnowledgeReindexWorker(
            governance=governance,
            rag_repository=RAGRepository(session, tenant_id=args.tenant_id),
            embedder=build_cached_embedder(settings),
            vector_store=build_vector_store(settings),
        )
        jobs = governance.pending_reindex_jobs(max(1, min(args.limit, 100)))
        for job in jobs:
            worker.process(job)
            session.commit()
            print(f"{job.job_id} {job.action} {job.status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
