from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.domain.fhir import resource_version
from app.fhir.identity import IdentityReconciler
from app.fhir.verification import verify_financial_claim
from app.fhir_canonical import normalize_resource
from app.models.fhir import (
    FHIRProvenanceModel,
    FHIRResourceSnapshotModel,
    HealthcareEventModel,
    HealthcareEventOutboxModel,
    HospitalCrossVerificationModel,
    PatientIdentityMatchModel,
)
from app.repositories.fhir import FHIRRepository


def _jsonable(value: object) -> dict[str, object]:
    if is_dataclass(value):
        raw = asdict(value)
        return {key: (str(val) if not isinstance(val, (str, int, float, bool, type(None), list, dict, tuple)) else val) for key, val in raw.items()}
    return dict(value) if isinstance(value, dict) else {"value": str(value)}


class FHIRIngestionService:
    def __init__(self, session: Session, tenant_id: str) -> None:
        self.session = session
        self.tenant_id = tenant_id
        self.repo = FHIRRepository(session, tenant_id)

    def persist_resource(self, *, connection_id: str, resource: dict[str, Any], source_url: str, claim_id: str | None = None, patient_subject_id: str | None = None, trace_id: str | None = None) -> FHIRResourceSnapshotModel:
        version = resource_version(resource, source_url)
        existing = self.repo.snapshot_by_version(connection_id, version.resource_type, version.logical_id, version.version_id)
        if existing:
            return existing
        canonical = _jsonable(normalize_resource(resource))
        canonical = json.loads(json.dumps(canonical, default=str))
        canonical_bytes = json.dumps(resource, sort_keys=True, separators=(",", ":")).encode()
        snapshot = FHIRResourceSnapshotModel(
            snapshot_id=f"fhir_{uuid.uuid4().hex}", tenant_id=self.tenant_id, connection_id=connection_id,
            claim_id=claim_id, patient_subject_id=patient_subject_id, resource_type=version.resource_type,
            logical_id=version.logical_id, version_id=version.version_id,
            last_updated=datetime.fromisoformat(version.last_updated.replace("Z", "+00:00")) if version.last_updated else None,
            source_url=source_url, content_sha256=hashlib.sha256(canonical_bytes).hexdigest(), raw_resource=resource,
            canonical_resource=canonical, authoritative=True, fetched_at=datetime.now(timezone.utc),
        )
        self.repo.add_snapshot(snapshot)
        self.session.add(FHIRProvenanceModel(
            provenance_id=f"prov_{uuid.uuid4().hex}", tenant_id=self.tenant_id, snapshot_id=snapshot.snapshot_id,
            source_system="fhir", source_endpoint=source_url, fetched_by="fhir_gateway", trace_id=trace_id,
            request_metadata={"resource_type": version.resource_type, "logical_id": version.logical_id, "version_id": version.version_id},
            recorded_at=datetime.now(timezone.utc),
        ))
        self._event("healthcare.fhir.resource.persisted", version.resource_type, snapshot.snapshot_id, claim_id, {"snapshot_id": snapshot.snapshot_id, "resource_type": version.resource_type, "logical_id": version.logical_id, "version_id": version.version_id}, f"persist:{connection_id}:{version.resource_type}:{version.logical_id}:{version.version_id}", trace_id)
        return snapshot

    def reconcile_patient(self, *, connection_id: str, patient_subject_id: str, internal_patient: dict[str, Any], fhir_patient: dict[str, Any]) -> PatientIdentityMatchModel:
        result = IdentityReconciler().compare(internal_patient, fhir_patient)
        model = PatientIdentityMatchModel(
            match_id=f"match_{uuid.uuid4().hex}", tenant_id=self.tenant_id, patient_subject_id=patient_subject_id,
            connection_id=connection_id, fhir_patient_id=str(fhir_patient["id"]), score=result.score, status=result.decision,
            reasons=list(result.reasons),
        )
        self.repo.add_identity_match(model)
        return model

    def verify_claim(self, *, claim_id: str, snapshot: FHIRResourceSnapshotModel, uploaded_claim: dict[str, Any], trace_id: str | None = None) -> HospitalCrossVerificationModel:
        result = verify_financial_claim(uploaded_claim, dict(snapshot.raw_resource))
        model = HospitalCrossVerificationModel(
            verification_id=f"verify_{uuid.uuid4().hex}", tenant_id=self.tenant_id, claim_id=claim_id,
            snapshot_id=snapshot.snapshot_id, verification_type="hospital_vs_uploaded_claim", status=result.status.value,
            confidence=result.confidence, findings=[asdict(item) for item in result.findings], input_snapshot=uploaded_claim,
            trace_id=trace_id,
        )
        self.repo.add_verification(model)
        self._event("healthcare.claim.cross_verified", "claim", claim_id, claim_id, {"verification_id": model.verification_id, "status": model.status, "confidence": float(model.confidence)}, f"verify:{claim_id}:{snapshot.snapshot_id}:hospital_vs_uploaded_claim", trace_id)
        return model

    def _event(self, event_type: str, aggregate_type: str, aggregate_id: str, claim_id: str | None, payload: dict[str, object], idempotency_key: str, trace_id: str | None) -> None:
        event_id = f"hevt_{uuid.uuid4().hex}"
        event = HealthcareEventModel(event_id=event_id, tenant_id=self.tenant_id, claim_id=claim_id, event_type=event_type, aggregate_type=aggregate_type, aggregate_id=aggregate_id, payload=payload, idempotency_key=idempotency_key, trace_id=trace_id, occurred_at=datetime.now(timezone.utc))
        outbox = HealthcareEventOutboxModel(outbox_id=f"hout_{uuid.uuid4().hex}", tenant_id=self.tenant_id, event_id=event_id, topic="medclaimiq.healthcare.events.v1", partition_key=claim_id or aggregate_id, payload={"event_id": event_id, "event_type": event_type, "aggregate_type": aggregate_type, "aggregate_id": aggregate_id, "claim_id": claim_id, "payload": payload})
        self.repo.add_event(event, outbox)
