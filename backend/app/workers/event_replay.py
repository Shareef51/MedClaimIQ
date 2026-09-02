from __future__ import annotations
import asyncio
from app.core.config import get_settings
from app.db.session import get_session_factory
from app.realtime.broker import KafkaEventProducer
from app.realtime.replay import EventReplayRelay

async def run_forever():
    s=get_settings(); producer=KafkaEventProducer(s.kafka_bootstrap_servers,client_id='medclaimiq-replay-relay')
    await producer.start()
    try:
        relay=EventReplayRelay(get_session_factory(),producer)
        while True:
            count=await relay.run_once(); await asyncio.sleep(0 if count else 1.0)
    finally: await producer.stop()
if __name__=='__main__': asyncio.run(run_forever())
