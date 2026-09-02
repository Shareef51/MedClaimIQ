from __future__ import annotations
import hashlib, json
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy.orm import Session
from app.domain.realtime import EventEnvelope
from app.models.realtime import RealtimeOutboxModel, RealtimeStreamEventModel
from app.observability.events import bind_event_trace

def canonical_sha256(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()

def enqueue_realtime_event(session: Session, *, envelope: EventEnvelope, topic: str) -> RealtimeOutboxModel:
    envelope = bind_event_trace(envelope)
    now = datetime.now(timezone.utc)
    data = envelope.model_dump(mode="json")
    row = RealtimeOutboxModel(
        outbox_id=f"rout_{uuid4().hex}", tenant_id=envelope.tenant_id, claim_id=envelope.claim_id,
        event_id=envelope.event_id, event_type=envelope.event_type, event_version=envelope.event_version,
        topic=topic, partition_key=envelope.partition_key(), envelope=data, status="pending",
        attempt_count=0, available_at=now, claimed_at=None, published_at=None,
    )
    session.add(row)
    # Transactional realtime projection contains metadata only; no raw evidence/document text.
    session.add(RealtimeStreamEventModel(
        event_id=envelope.event_id, tenant_id=envelope.tenant_id, claim_id=envelope.claim_id,
        topic=topic, event_type=envelope.event_type, event_version=envelope.event_version,
        envelope_sha256=canonical_sha256(data), stream_payload={
            "event_id": envelope.event_id, "event_type": envelope.event_type,
            "aggregate_type": envelope.aggregate_type, "aggregate_id": envelope.aggregate_id,
            "trace_id": envelope.trace_id, "metadata": envelope.metadata,
        }, occurred_at=envelope.occurred_at,
    ))
    session.flush()
    return row
