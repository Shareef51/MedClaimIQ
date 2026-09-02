from __future__ import annotations
import asyncio, json
from app.repositories.realtime import RealtimeRepository

class ClaimRealtimeStreamer:
    def __init__(self, session_factory, tenant_id:str, claim_id:str, after_sequence:int=0, poll_seconds:float=0.75):
        self.session_factory=session_factory; self.tenant_id=tenant_id; self.claim_id=claim_id; self.cursor=after_sequence; self.poll_seconds=poll_seconds
    async def events(self,is_disconnected):
        while not await is_disconnected():
            with self.session_factory() as db:
                rows=RealtimeRepository(db,self.tenant_id).events_after(self.claim_id,self.cursor,100)
                for row in rows:
                    self.cursor=row.stream_sequence
                    payload={"sequence":row.stream_sequence,"event_id":row.event_id,"event_type":row.event_type,"topic":row.topic,"occurred_at":row.occurred_at.isoformat(),"published":row.published_at is not None,"data":row.stream_payload}
                    yield f"id: {row.stream_sequence}\nevent: {row.event_type}\ndata: {json.dumps(payload,separators=(',',':'))}\n\n"
            await asyncio.sleep(self.poll_seconds)


class TenantRealtimeStreamer:
    """Tenant-scoped SSE streamer for metadata-only operational events.

    The caller supplies an allowlisted event prefix tuple; this class never emits
    raw evidence content and reuses the global monotonic stream_sequence cursor.
    """
    def __init__(self, session_factory, tenant_id: str, after_sequence: int = 0, event_prefixes: tuple[str, ...] = (), poll_seconds: float = 0.75):
        self.session_factory = session_factory
        self.tenant_id = tenant_id
        self.cursor = after_sequence
        self.event_prefixes = event_prefixes
        self.poll_seconds = poll_seconds

    async def events(self, is_disconnected):
        while not await is_disconnected():
            with self.session_factory() as db:
                rows = RealtimeRepository(db, self.tenant_id).tenant_events_after(
                    self.cursor, 100, self.event_prefixes
                )
                for row in rows:
                    self.cursor = row.stream_sequence
                    payload = {
                        "sequence": row.stream_sequence,
                        "event_id": row.event_id,
                        "event_type": row.event_type,
                        "claim_id": row.claim_id,
                        "topic": row.topic,
                        "occurred_at": row.occurred_at.isoformat(),
                        "published": row.published_at is not None,
                        "data": row.stream_payload,
                    }
                    yield f"id: {row.stream_sequence}\nevent: {row.event_type}\ndata: {json.dumps(payload,separators=(',',':'))}\n\n"
            await asyncio.sleep(self.poll_seconds)

class PortalClaimRealtimeStreamer:
    """Claim-scoped external stream that exposes only portal-safe event classes.

    Internal agent, guardrail, fraud/risk, reviewer-note, MCP, and graph events are
    intentionally skipped even though they may share the same underlying stream.
    """
    SAFE_PREFIXES = (
        "claim.", "portal.", "evidence.upload.", "evidence.ingestion.",
        "healthcare.claim.cross_verified", "sla.timer.warning", "sla.timer.breached", "appeal.", "communication.",
    )
    BLOCKED_TOKENS = ("agent", "guardrail", "fraud", "risk", "critic", "review.", "mcp", "graph")
    def __init__(self, session_factory, tenant_id: str, claim_id: str, after_sequence: int = 0, poll_seconds: float = 0.75):
        self.session_factory=session_factory; self.tenant_id=tenant_id; self.claim_id=claim_id; self.cursor=after_sequence; self.poll_seconds=poll_seconds
    def _safe(self,event_type:str)->bool:
        lowered=event_type.lower()
        return any(event_type.startswith(p) for p in self.SAFE_PREFIXES) and not any(token in lowered for token in self.BLOCKED_TOKENS)
    async def events(self,is_disconnected):
        while not await is_disconnected():
            with self.session_factory() as db:
                rows=RealtimeRepository(db,self.tenant_id).events_after(self.claim_id,self.cursor,100)
                for row in rows:
                    self.cursor=row.stream_sequence
                    if not self._safe(row.event_type):
                        continue
                    payload={"sequence":row.stream_sequence,"event_id":row.event_id,"event_type":row.event_type,"occurred_at":row.occurred_at.isoformat(),"data":_portal_payload(row.event_type,row.stream_payload)}
                    yield f"id: {row.stream_sequence}\nevent: portal.update\ndata: {json.dumps(payload,separators=(',',':'))}\n\n"
            await asyncio.sleep(self.poll_seconds)

def _portal_payload(event_type:str,payload:dict)->dict:
    """Reduce internal event payloads to a minimal external-safe shape."""
    allowed={"status","to_status","request_id","submission_id","acknowledgement_code","timer_type","due_at","warning_index","verification_status","notice_id","appeal_id","resolution_id","audience","delivery_status","task_type"}
    return {k:v for k,v in (payload or {}).items() if k in allowed}
