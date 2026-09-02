"""Operational example for a worker-driven FHIR sync.

This script intentionally requires an existing persisted FHIR connection and is not
run automatically. Use only synthetic/de-identified endpoints in portfolio/demo mode.
"""
from __future__ import annotations

import argparse

from app.core.config import get_settings
from app.db.session import get_session_factory
from app.fhir.gateway import FHIRGateway
from app.workers.fhir_sync import FHIRSyncRequest, sync_resources


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument('--tenant-id', required=True)
    parser.add_argument('--connection-id', required=True)
    parser.add_argument('--resource-type', required=True)
    parser.add_argument('--patient')
    args=parser.parse_args()
    settings=get_settings()
    gateway=FHIRGateway(base_url=settings.fhir_default_base_url, timeout_seconds=settings.fhir_http_timeout_seconds, max_attempts=settings.fhir_max_attempts, rate_per_second=settings.fhir_rate_limit_per_second)
    db=get_session_factory()()
    try:
        params={'patient':args.patient} if args.patient else {}
        result=sync_resources(db=db,gateway=gateway,request=FHIRSyncRequest(tenant_id=args.tenant_id,connection_id=args.connection_id,resource_type=args.resource_type,search_params=params))
        db.commit()
        print({'fetched':result.fetched,'snapshots':result.persisted_snapshot_ids})
    except Exception:
        db.rollback(); raise
    finally:
        gateway.close(); db.close()


if __name__ == '__main__': main()
