from __future__ import annotations

import argparse

from app.core.agent_factory import build_production_specialist_registry
from app.core.config import get_settings
from app.db.session import get_session_factory
from app.orchestration.runner import LangGraphWorkflowRunner


def main() -> None:
    parser = argparse.ArgumentParser(description="Execute one persisted MedClaimIQ agent workflow.")
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--claim-id", required=True)
    parser.add_argument("--workflow-id", required=True)
    parser.add_argument("--trace-id")
    args = parser.parse_args()

    settings = get_settings()
    session_factory = get_session_factory()
    runner = LangGraphWorkflowRunner(
        session_factory=session_factory,
        settings=settings,
        registry_factory=lambda db, tenant_id: build_production_specialist_registry(db, tenant_id, settings),
    )
    result = runner.execute(
        tenant_id=args.tenant_id,
        claim_id=args.claim_id,
        workflow_id=args.workflow_id,
        trace_id=args.trace_id,
    )
    print({
        "workflow_id": result.workflow_id,
        "status": result.status,
        "checkpoint_id": result.checkpoint_id,
    })


if __name__ == "__main__":
    main()
