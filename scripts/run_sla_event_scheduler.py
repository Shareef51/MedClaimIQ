from __future__ import annotations

import asyncio

from app.core.config import get_settings
from app.db.session import get_session_factory
from app.domain.realtime import EventTopic
from app.realtime.broker import KafkaEventProducer
from app.realtime.consumer import DurableEventProcessor, KafkaConsumerWorker
from app.workers.sla_event_scheduler import handle_sla_source_event


async def main() -> None:
    settings = get_settings()
    processor = DurableEventProcessor(
        get_session_factory(), consumer_group="medclaimiq-sla-scheduler-v1",
        max_attempts=settings.event_consumer_max_attempts,
    )
    producer = KafkaEventProducer(settings.kafka_bootstrap_servers, client_id="medclaimiq-sla-scheduler")
    worker = KafkaConsumerWorker(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        topics=[EventTopic.CLAIMS.value, EventTopic.HEALTHCARE.value, EventTopic.MCP.value],
        consumer_group="medclaimiq-sla-scheduler-v1", processor=processor,
        producer=producer, handler=handle_sla_source_event,
        max_inflight=settings.event_worker_max_inflight,
        pause_threshold=settings.event_worker_pause_threshold,
    )
    await worker.run_forever()


if __name__ == "__main__":
    asyncio.run(main())
