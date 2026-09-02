from __future__ import annotations
import json
from dataclasses import dataclass
from typing import Protocol

@dataclass(frozen=True, slots=True)
class PublishResult:
    topic: str; partition: int | None=None; offset: int | None=None

class EventProducer(Protocol):
    async def start(self)->None: ...
    async def stop(self)->None: ...
    async def send(self, *, topic:str, key:str, value:dict, headers:list[tuple[str,bytes]]|None=None)->PublishResult: ...

class KafkaEventProducer:
    def __init__(self, bootstrap_servers: str, client_id: str="medclaimiq-outbox-relay") -> None:
        self.bootstrap_servers=bootstrap_servers; self.client_id=client_id; self._producer=None
    async def start(self):
        from aiokafka import AIOKafkaProducer
        self._producer=AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers, client_id=self.client_id,
            acks="all", enable_idempotence=True, linger_ms=5,
            value_serializer=lambda v: json.dumps(v, separators=(",",":"), default=str).encode(),
            key_serializer=lambda v: v.encode(),
        )
        await self._producer.start()
    async def stop(self):
        if self._producer is not None: await self._producer.stop()
    async def send(self, *, topic, key, value, headers=None):
        if self._producer is None: raise RuntimeError("producer not started")
        md=await self._producer.send_and_wait(topic, key=key, value=value, headers=headers or [])
        return PublishResult(topic=md.topic, partition=md.partition, offset=md.offset)

class MemoryEventProducer:
    def __init__(self): self.messages=[]
    async def start(self): return None
    async def stop(self): return None
    async def send(self, *, topic, key, value, headers=None):
        self.messages.append((topic,key,value,headers or [])); return PublishResult(topic,0,len(self.messages)-1)
