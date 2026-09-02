from __future__ import annotations
import asyncio
from app.core.config import get_settings
from app.db.session import get_session_factory
from app.realtime.broker import KafkaEventProducer
from app.realtime.outbox import OutboxRelay

async def run_forever():
    s=get_settings(); producer=KafkaEventProducer(s.kafka_bootstrap_servers)
    await producer.start()
    try:
        relay=OutboxRelay(get_session_factory(),producer,batch_size=s.event_outbox_batch_size,retry_base_seconds=s.event_retry_base_seconds,max_attempts=s.event_outbox_max_attempts)
        while True:
            count=await relay.relay_once()
            await asyncio.sleep(0 if count else s.event_outbox_poll_seconds)
    finally: await producer.stop()

if __name__=="__main__": asyncio.run(run_forever())
