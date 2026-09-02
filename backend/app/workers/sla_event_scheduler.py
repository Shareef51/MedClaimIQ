from __future__ import annotations

from app.domain.realtime import EventEnvelope
from app.services.sla import SLAService


def handle_sla_source_event(db, envelope: EventEnvelope) -> list[str]:
    """Idempotent event-consumer handler for timer creation/completion."""
    return SLAService(db, envelope.tenant_id).handle_event(envelope)
