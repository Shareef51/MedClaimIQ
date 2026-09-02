from __future__ import annotations
# Production consumer runtime is intentionally thin: domain handlers are injected into
# DurableEventProcessor so dedup/retry/DLQ semantics stay independent from business logic.
from app.realtime.consumer import DurableEventProcessor
__all__=["DurableEventProcessor"]
