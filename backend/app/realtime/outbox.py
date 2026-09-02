from __future__ import annotations
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.domain.realtime import EventEnvelope
from app.models.realtime import RealtimeOutboxModel, RealtimeStreamEventModel
from app.models.ingestion import EvidenceEventOutboxModel, EvidenceProcessingEventModel
from app.models.fhir import HealthcareEventOutboxModel, HealthcareEventModel
from app.realtime.events import canonical_sha256
from app.observability.events import kafka_trace_headers
from app.observability.tracing import traced_operation

class OutboxRelay:
    def __init__(self, session_factory, producer, *, batch_size:int=100, retry_base_seconds:int=5, max_attempts:int=10):
        self.session_factory=session_factory; self.producer=producer; self.batch_size=batch_size; self.retry_base_seconds=retry_base_seconds; self.max_attempts=max_attempts

    async def relay_once(self)->int:
        count=0
        with self.session_factory() as db:
            rows=list(db.scalars(select(RealtimeOutboxModel).where(RealtimeOutboxModel.status.in_(["pending","retry"]), RealtimeOutboxModel.available_at<=datetime.now(timezone.utc)).order_by(RealtimeOutboxModel.created_at).limit(self.batch_size).with_for_update(skip_locked=True)))
            for row in rows:
                count += await self._publish_generic(db,row)
            # Legacy transactional outboxes from ingestion/FHIR are relayed directly.
            erows=list(db.scalars(select(EvidenceEventOutboxModel).where(EvidenceEventOutboxModel.published_at.is_(None)).order_by(EvidenceEventOutboxModel.created_at).limit(self.batch_size).with_for_update(skip_locked=True)))
            for row in erows:
                event=db.get(EvidenceProcessingEventModel,row.event_id)
                if event: count += await self._publish_legacy(db,row,event,"evidence")
            hrows=list(db.scalars(select(HealthcareEventOutboxModel).where(HealthcareEventOutboxModel.published_at.is_(None)).order_by(HealthcareEventOutboxModel.created_at).limit(self.batch_size).with_for_update(skip_locked=True)))
            for row in hrows:
                event=db.get(HealthcareEventModel,row.event_id)
                if event: count += await self._publish_legacy(db,row,event,"healthcare")
            db.commit()
        return count

    async def _publish_generic(self, db:Session,row:RealtimeOutboxModel)->int:
        try:
            with traced_operation("kafka.outbox.publish", kind="producer", attributes={"topic": row.topic, "event_type": row.event_type}):
                await self.producer.send(topic=row.topic,key=row.partition_key,value=dict(row.envelope),headers=self._headers(row.envelope))
            row.status="published"; row.published_at=datetime.now(timezone.utc); row.attempt_count+=1
            stream=db.scalar(select(RealtimeStreamEventModel).where(RealtimeStreamEventModel.event_id==row.event_id))
            if stream: stream.published_at=row.published_at
            return 1
        except Exception as exc:
            row.attempt_count+=1; row.last_error_code=type(exc).__name__; row.last_error_detail=str(exc)[:500]
            row.status="failed" if row.attempt_count>=self.max_attempts else "retry"
            row.available_at=datetime.now(timezone.utc)+timedelta(seconds=min(300,self.retry_base_seconds*(2**max(0,row.attempt_count-1))))
            return 0

    async def _publish_legacy(self,db,row,event,producer_name)->int:
        env=EventEnvelope(event_id=event.event_id,event_type=event.event_type,tenant_id=event.tenant_id,claim_id=getattr(event,"claim_id",None),aggregate_type=event.aggregate_type,aggregate_id=event.aggregate_id,occurred_at=event.occurred_at,trace_id=getattr(event,"trace_id",None),producer=f"medclaimiq-{producer_name}",payload=dict(event.payload))
        try:
            await self.producer.send(topic=row.topic,key=row.partition_key,value=env.model_dump(mode="json"),headers=self._headers(env.model_dump(mode="json")))
            row.published_at=datetime.now(timezone.utc)
            if hasattr(row,"status"): row.status="published"
            if hasattr(row,"attempt_count"): row.attempt_count+=1
            if hasattr(row,"publish_attempts"): row.publish_attempts+=1
            existing=db.scalar(select(RealtimeStreamEventModel).where(RealtimeStreamEventModel.event_id==event.event_id))
            if not existing:
                data=env.model_dump(mode="json")
                db.add(RealtimeStreamEventModel(event_id=env.event_id,tenant_id=env.tenant_id,claim_id=env.claim_id,topic=row.topic,event_type=env.event_type,event_version=env.event_version,envelope_sha256=canonical_sha256(data),stream_payload={"event_id":env.event_id,"event_type":env.event_type,"aggregate_type":env.aggregate_type,"aggregate_id":env.aggregate_id,"trace_id":env.trace_id},occurred_at=env.occurred_at,published_at=row.published_at))
            return 1
        except Exception as exc:
            if hasattr(row,"attempt_count"): row.attempt_count+=1
            if hasattr(row,"publish_attempts"): row.publish_attempts+=1
            if hasattr(row,"last_error_detail"): row.last_error_detail=str(exc)[:500]
            if hasattr(row,"last_error"): row.last_error=str(exc)[:500]
            return 0

    @staticmethod
    def _headers(env:dict):
        headers=[("event-type",str(env.get("event_type","")).encode()),("event-version",str(env.get("event_version","1.0")).encode())]
        if env.get("trace_id"): headers.append(("trace-id",str(env["trace_id"]).encode()))
        headers.extend(kafka_trace_headers(env))
        return headers
