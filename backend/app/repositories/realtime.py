from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import set_tenant_context
from app.models.realtime import EventConsumerReceiptModel, EventDeadLetterModel, EventReplayRequestModel, RealtimeStreamEventModel

class RealtimeRepository:
    def __init__(self, session: Session, tenant_id: str) -> None:
        self.session=session; self.tenant_id=tenant_id; set_tenant_context(session, tenant_id)
    def events_after(self, claim_id: str, after_sequence: int=0, limit: int=100):
        return list(self.session.scalars(select(RealtimeStreamEventModel).where(
            RealtimeStreamEventModel.tenant_id==self.tenant_id,
            RealtimeStreamEventModel.claim_id==claim_id,
            RealtimeStreamEventModel.stream_sequence>after_sequence,
        ).order_by(RealtimeStreamEventModel.stream_sequence).limit(max(1,min(limit,500)))))
    def tenant_events_after(self, after_sequence: int=0, limit: int=100, event_prefixes: tuple[str, ...]=()):
        stmt = select(RealtimeStreamEventModel).where(
            RealtimeStreamEventModel.tenant_id == self.tenant_id,
            RealtimeStreamEventModel.stream_sequence > after_sequence,
        )
        if event_prefixes:
            from sqlalchemy import or_
            stmt = stmt.where(or_(*[RealtimeStreamEventModel.event_type.like(f"{prefix}%") for prefix in event_prefixes]))
        return list(self.session.scalars(
            stmt.order_by(RealtimeStreamEventModel.stream_sequence).limit(max(1, min(limit, 500)))
        ))
    def receipt(self, consumer_group: str, event_id: str):
        return self.session.scalar(select(EventConsumerReceiptModel).where(EventConsumerReceiptModel.consumer_group==consumer_group, EventConsumerReceiptModel.event_id==event_id))
    def add_receipt(self, row): self.session.add(row); self.session.flush(); return row
    def add_dead_letter(self,row): self.session.add(row); self.session.flush(); return row
    def get_dead_letter(self, dlq_id: str):
        return self.session.scalar(select(EventDeadLetterModel).where(EventDeadLetterModel.tenant_id==self.tenant_id, EventDeadLetterModel.dead_letter_id==dlq_id))
    def add_replay(self,row): self.session.add(row); self.session.flush(); return row
    def list_dead_letters(self, claim_id: str, limit:int=100):
        return list(self.session.scalars(select(EventDeadLetterModel).where(EventDeadLetterModel.tenant_id==self.tenant_id, EventDeadLetterModel.claim_id==claim_id).order_by(EventDeadLetterModel.created_at.desc()).limit(limit)))
