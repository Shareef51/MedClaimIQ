from __future__ import annotations

from app.domain.realtime import EventEnvelope
from app.observability.tracing import current_trace_context, current_trace_id


def bind_event_trace(envelope: EventEnvelope) -> EventEnvelope:
    ctx = current_trace_context()
    updates = {}
    if not envelope.trace_id and current_trace_id(): updates["trace_id"] = current_trace_id()
    if ctx and not envelope.traceparent: updates["traceparent"] = ctx.traceparent
    return envelope.model_copy(update=updates) if updates else envelope


def kafka_trace_headers(envelope: dict) -> list[tuple[str, bytes]]:
    headers: list[tuple[str, bytes]] = []
    if envelope.get("traceparent"): headers.append(("traceparent", str(envelope["traceparent"]).encode()))
    if envelope.get("tracestate"): headers.append(("tracestate", str(envelope["tracestate"]).encode()))
    return headers
