from __future__ import annotations
from datetime import datetime, timezone
from hashlib import sha256
from uuid import uuid4
from app.domain.realtime import EventEnvelope
from app.models.realtime import EventReplayRequestModel
from app.repositories.realtime import RealtimeRepository

class EventReplayService:
    def __init__(self, session, tenant_id:str): self.session=session; self.repo=RealtimeRepository(session,tenant_id); self.tenant_id=tenant_id
    def request(self, *, dead_letter_id:str, user_id:str, reason:str):
        dlq=self.repo.get_dead_letter(dead_letter_id)
        if dlq is None: raise ValueError("dead letter not found in tenant scope")
        row=EventReplayRequestModel(replay_id=f"erp_{uuid4().hex}",tenant_id=self.tenant_id,claim_id=dlq.claim_id,dead_letter_id=dlq.dead_letter_id,requested_by_user_id=user_id,reason_sha256=sha256(reason.encode()).hexdigest(),target_topic=dlq.source_topic,status="pending",created_at=datetime.now(timezone.utc))
        return self.repo.add_replay(row)
    def envelope(self, replay_id:str):
        from sqlalchemy import select
        row=self.session.scalar(select(EventReplayRequestModel).where(EventReplayRequestModel.tenant_id==self.tenant_id,EventReplayRequestModel.replay_id==replay_id))
        if row is None: raise ValueError("replay request not found")
        dlq=self.repo.get_dead_letter(row.dead_letter_id)
        if dlq is None: raise ValueError("dead letter missing")
        return EventEnvelope.model_validate(dlq.replay_envelope), row.target_topic

class EventReplayRelay:
    def __init__(self, session_factory, producer, *, batch_size:int=50): self.session_factory=session_factory; self.producer=producer; self.batch_size=batch_size
    async def run_once(self)->int:
        from sqlalchemy import select
        from app.models.realtime import EventReplayRequestModel, EventDeadLetterModel
        count=0
        with self.session_factory() as db:
            rows=list(db.scalars(select(EventReplayRequestModel).where(EventReplayRequestModel.status=='pending').order_by(EventReplayRequestModel.created_at).limit(self.batch_size).with_for_update(skip_locked=True)))
            for row in rows:
                dlq=db.get(EventDeadLetterModel,row.dead_letter_id)
                if dlq is None:
                    row.status='failed'; continue
                env=EventEnvelope.model_validate(dlq.replay_envelope)
                await self.producer.send(topic=row.target_topic,key=env.partition_key(),value=env.model_dump(mode='json'),headers=[('x-replay-id',row.replay_id.encode()),('x-original-event-id',env.event_id.encode())])
                now=datetime.now(timezone.utc); row.status='executed'; row.executed_at=now; dlq.replayed=True; dlq.replayed_at=now; count+=1
            db.commit()
        return count
