from __future__ import annotations

import argparse

from app.core.config import get_settings
from app.core.ingestion_factory import build_malware_scanner, build_object_storage
from app.db.session import get_session_factory, set_tenant_context
from app.services.ingestion import IngestionInvariantError
from app.workers.evidence_ingestion import EvidenceIngestionWorker


def main() -> None:
    parser = argparse.ArgumentParser(description="Process one quarantined MedClaimIQ evidence upload.")
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--upload-session-id", required=True)
    args = parser.parse_args()

    settings = get_settings()
    db = get_session_factory()()
    try:
        set_tenant_context(db, args.tenant_id)
        worker = EvidenceIngestionWorker(
            db,
            args.tenant_id,
            storage=build_object_storage(settings),
            scanner=build_malware_scanner(settings),
            bucket_name=settings.s3_bucket,
            malware_scan_required=settings.malware_scan_required,
        )
        upload = worker.process(args.upload_session_id)
        db.commit()
        print(f"upload_session_id={upload.upload_session_id} status={upload.status}")
    except IngestionInvariantError as exc:
        if exc.persist_state:
            db.commit()
        else:
            db.rollback()
        raise SystemExit(f"ingestion_error={exc.code}") from exc
    finally:
        db.close()


if __name__ == "__main__":
    main()
