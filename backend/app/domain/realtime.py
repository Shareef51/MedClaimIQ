from __future__ import annotations
from datetime import datetime
from enum import StrEnum
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

class EventTopic(StrEnum):
    CLAIMS = "medclaimiq.claim.events.v1"
    EVIDENCE = "medclaimiq.evidence.events.v1"
    HEALTHCARE = "medclaimiq.healthcare.events.v1"
    AGENTS = "medclaimiq.agent.events.v1"
    MCP = "medclaimiq.mcp.events.v1"
    SLA = "medclaimiq.sla.events.v1"

class EventEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_id: str
    event_type: str
    event_version: str = "1.0"
    tenant_id: str
    claim_id: str | None = None
    aggregate_type: str
    aggregate_id: str
    occurred_at: datetime
    trace_id: str | None = None
    traceparent: str | None = None
    tracestate: str | None = None
    correlation_id: str | None = None
    causation_id: str | None = None
    producer: str
    payload: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def partition_key(self) -> str:
        return self.claim_id or self.aggregate_id

class ConsumerDecision(StrEnum):
    ACK = "ack"
    RETRY = "retry"
    DLQ = "dlq"

TOPIC_VALUES = tuple(item.value for item in EventTopic)
