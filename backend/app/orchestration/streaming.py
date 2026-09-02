from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Callable

from sqlalchemy.orm import Session

from app.repositories.orchestration import OrchestrationRepository


class WorkflowEventStreamer:
    """SSE tailer over the append-only workflow event log.

    It opens a short-lived tenant-scoped database session per poll instead of holding a
    request transaction open for the lifetime of the stream.
    """

    def __init__(
        self,
        *,
        session_factory: Callable[[], Session],
        tenant_id: str,
        workflow_id: str,
        after_sequence: int = 0,
        poll_seconds: float = 0.75,
        heartbeat_seconds: float = 15.0,
    ) -> None:
        self.session_factory = session_factory
        self.tenant_id = tenant_id
        self.workflow_id = workflow_id
        self.after_sequence = max(0, after_sequence)
        self.poll_seconds = max(0.2, poll_seconds)
        self.heartbeat_seconds = max(5.0, heartbeat_seconds)

    async def events(self, is_disconnected: Callable[[], object]) -> AsyncIterator[str]:
        cursor = self.after_sequence
        since_heartbeat = 0.0
        while True:
            disconnected = is_disconnected()
            if hasattr(disconnected, "__await__"):
                disconnected = await disconnected
            if disconnected:
                break
            with self.session_factory() as db:
                rows = OrchestrationRepository(db, self.tenant_id).events_after(
                    self.workflow_id, after_sequence=cursor, limit=100
                )
            if rows:
                for row in rows:
                    cursor = row.sequence
                    payload = {
                        "sequence": row.sequence,
                        "event_type": row.event_type,
                        "actor_type": row.actor_type,
                        "actor_id": row.actor_id,
                        "payload": row.event_payload,
                        "trace_id": row.trace_id,
                        "occurred_at": row.occurred_at.isoformat(),
                    }
                    yield f"id: {row.sequence}\nevent: {row.event_type}\ndata: {json.dumps(payload, separators=(',', ':'))}\n\n"
                since_heartbeat = 0.0
            else:
                await asyncio.sleep(self.poll_seconds)
                since_heartbeat += self.poll_seconds
                if since_heartbeat >= self.heartbeat_seconds:
                    yield ": heartbeat\n\n"
                    since_heartbeat = 0.0
