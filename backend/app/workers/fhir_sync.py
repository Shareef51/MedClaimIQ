from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.fhir.gateway import FHIRGateway
from app.services.fhir import FHIRIngestionService


@dataclass(frozen=True)
class FHIRSyncRequest:
    tenant_id: str
    connection_id: str
    resource_type: str
    search_params: dict[str, Any]
    claim_id: str | None = None
    patient_subject_id: str | None = None
    trace_id: str | None = None


@dataclass(frozen=True)
class FHIRSyncResult:
    fetched: int
    persisted_snapshot_ids: tuple[str, ...]


def sync_resources(*, db: Session, gateway: FHIRGateway, request: FHIRSyncRequest) -> FHIRSyncResult:
    """Fetch and persist one bounded resource set using immutable version snapshots.

    Broker/worker runtimes can call this function from healthcare sync events. The
    transaction is owned by the worker so database snapshots/outbox rows commit together.
    """
    service = FHIRIngestionService(db, request.tenant_id)
    resources = gateway.search(request.resource_type, params=request.search_params)
    snapshot_ids: list[str] = []
    for resource in resources:
        logical_id = str(resource.get("id") or "")
        source_url = f"{gateway.base_url}{request.resource_type}/{logical_id}"
        snapshot = service.persist_resource(
            connection_id=request.connection_id,
            resource=resource,
            source_url=source_url,
            claim_id=request.claim_id,
            patient_subject_id=request.patient_subject_id,
            trace_id=request.trace_id,
        )
        snapshot_ids.append(snapshot.snapshot_id)
    return FHIRSyncResult(fetched=len(resources), persisted_snapshot_ids=tuple(snapshot_ids))
