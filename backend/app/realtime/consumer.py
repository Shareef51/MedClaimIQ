from __future__ import annotations
import hashlib, json
from datetime import datetime, timezone
from uuid import uuid4
from app.domain.realtime import EventEnvelope
from app.models.realtime import EventConsumerReceiptModel, EventDeadLetterModel
from app.repositories.realtime import RealtimeRepository
from app.observability.tracing import extracted_trace_operation

class RetryableEventError(RuntimeError): pass
class PermanentEventError(RuntimeError): pass

class DurableEventProcessor:
    def __init__(self, session_factory, *, consumer_group:str, max_attempts:int=3):
        self.session_factory=session_factory; self.consumer_group=consumer_group; self.max_attempts=max_attempts
    def process(self, *, envelope:EventEnvelope, topic:str, handler, partition:int|None=None, offset:int|None=None, attempt:int=1):
        with self.session_factory() as db:
            repo=RealtimeRepository(db,envelope.tenant_id)
            existing=repo.receipt(self.consumer_group,envelope.event_id)
            if existing and existing.status=="completed": return "duplicate"
            try:
                handler(db,envelope)
                if existing is None:
                    repo.add_receipt(EventConsumerReceiptModel(receipt_id=f"erc_{uuid4().hex}",tenant_id=envelope.tenant_id,claim_id=envelope.claim_id,event_id=envelope.event_id,consumer_group=self.consumer_group,topic=topic,partition=partition,offset=offset,status="completed",attempt_count=attempt,processed_at=datetime.now(timezone.utc)))
                else:
                    existing.status="completed"; existing.attempt_count=attempt; existing.processed_at=datetime.now(timezone.utc)
                db.commit(); return "completed"
            except RetryableEventError as exc:
                db.rollback()
                if attempt < self.max_attempts: return "retry"
                self._dlq(envelope,topic,exc,attempt); return "dlq"
            except Exception as exc:
                db.rollback(); self._dlq(envelope,topic,exc,attempt); return "dlq"
    def _dlq(self,envelope,topic,exc,attempt):
        with self.session_factory() as db:
            repo=RealtimeRepository(db,envelope.tenant_id); raw=envelope.model_dump(mode="json")
            canonical=json.dumps(raw,sort_keys=True,separators=(",",":"),default=str)
            repo.add_dead_letter(EventDeadLetterModel(dead_letter_id=f"edl_{uuid4().hex}",tenant_id=envelope.tenant_id,claim_id=envelope.claim_id,event_id=envelope.event_id,source_topic=topic,consumer_group=self.consumer_group,attempt_count=attempt,envelope_sha256=hashlib.sha256(canonical.encode()).hexdigest(),replay_envelope=raw,error_code=type(exc).__name__,error_detail_sha256=hashlib.sha256(str(exc).encode()).hexdigest(),replayed=False,created_at=datetime.now(timezone.utc)))
            db.commit()

def retry_topic(source_topic: str, attempt: int) -> str:
    return f"{source_topic}.retry.{max(1, attempt)}"

def dead_letter_topic(source_topic: str) -> str:
    return f"{source_topic}.dlq"

class BoundedWorkerPool:
    """Backpressure helper for Kafka consumers.

    Runtime consumers pause broker partitions when `paused` is true and resume
    them once in-flight work drops below the pause threshold.
    """
    def __init__(self, *, max_inflight: int, pause_threshold: int) -> None:
        if max_inflight < 1 or pause_threshold < 1 or pause_threshold > max_inflight:
            raise ValueError("invalid worker backpressure thresholds")
        self.max_inflight=max_inflight; self.pause_threshold=pause_threshold; self.inflight=0
    @property
    def paused(self) -> bool: return self.inflight >= self.pause_threshold
    def acquire(self) -> None:
        if self.inflight >= self.max_inflight: raise RuntimeError("worker pool saturated")
        self.inflight += 1
    def release(self) -> None: self.inflight=max(0,self.inflight-1)

class KafkaConsumerWorker:
    """Async Kafka runtime with manual commits, retry topics and partition backpressure."""
    def __init__(self, *, bootstrap_servers:str, topics:list[str], consumer_group:str, processor:DurableEventProcessor, producer, handler, max_inflight:int=32, pause_threshold:int=24):
        self.bootstrap_servers=bootstrap_servers; self.topics=topics; self.consumer_group=consumer_group
        self.processor=processor; self.producer=producer; self.handler=handler
        self.pool=BoundedWorkerPool(max_inflight=max_inflight,pause_threshold=pause_threshold)
    async def run_forever(self):
        import json
        from aiokafka import AIOKafkaConsumer
        consumer=AIOKafkaConsumer(*self.topics,bootstrap_servers=self.bootstrap_servers,group_id=self.consumer_group,enable_auto_commit=False,value_deserializer=lambda b:json.loads(b.decode()))
        await consumer.start(); await self.producer.start()
        try:
            async for msg in consumer:
                if self.pool.paused:
                    assigned=consumer.assignment()
                    if assigned: consumer.pause(*assigned)
                self.pool.acquire()
                try:
                    env=EventEnvelope.model_validate(msg.value)
                    attempt=1
                    carrier={}
                    for key,value in (msg.headers or []):
                        decoded=value.decode()
                        carrier[key]=decoded
                        if key=='x-retry-attempt': attempt=int(decoded)
                    if env.traceparent and "traceparent" not in carrier: carrier["traceparent"]=env.traceparent
                    if env.tracestate and "tracestate" not in carrier: carrier["tracestate"]=env.tracestate
                    with extracted_trace_operation("kafka.event.consume", carrier=carrier, attributes={"topic":msg.topic,"event_type":env.event_type,"consumer_group":self.consumer_group}):
                        outcome=self.processor.process(envelope=env,topic=msg.topic,handler=self.handler,partition=msg.partition,offset=msg.offset,attempt=attempt)
                    if outcome=='retry':
                        await self.producer.send(topic=retry_topic(msg.topic,attempt+1),key=env.partition_key(),value=env.model_dump(mode='json'),headers=[('x-retry-attempt',str(attempt+1).encode())])
                    elif outcome=='dlq':
                        await self.producer.send(topic=dead_letter_topic(msg.topic),key=env.partition_key(),value=env.model_dump(mode='json'),headers=[('x-final-attempt',str(attempt).encode())])
                    await consumer.commit()
                finally:
                    self.pool.release()
                    if not self.pool.paused:
                        assigned=consumer.assignment()
                        if assigned: consumer.resume(*assigned)
        finally:
            await self.producer.stop(); await consumer.stop()
