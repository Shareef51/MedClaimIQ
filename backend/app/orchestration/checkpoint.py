from __future__ import annotations

import os
from contextlib import contextmanager
from dataclasses import asdict
from typing import Any, Iterator


class LangGraphPostgresCheckpointerFactory:
    """Lifecycle-safe LangGraph Postgres checkpointer factory.

    PostgreSQL checkpoint deserialization is restricted by default. The checkpointer's
    own schema is initialized with setup() at application/worker startup, not per node.
    """

    def __init__(self, database_uri: str, *, strict_msgpack: bool = True) -> None:
        self.database_uri = database_uri
        self.strict_msgpack = strict_msgpack

    @staticmethod
    def psycopg_uri(database_uri: str) -> str:
        return database_uri.replace("postgresql+psycopg://", "postgresql://", 1)

    @contextmanager
    def open(self) -> Iterator[Any]:
        if self.strict_msgpack:
            os.environ.setdefault("LANGGRAPH_STRICT_MSGPACK", "true")
        try:
            from langgraph.checkpoint.postgres import PostgresSaver
        except ImportError as exc:  # pragma: no cover - runtime dependency
            raise RuntimeError("langgraph-checkpoint-postgres is required for durable workflows") from exc
        with PostgresSaver.from_conn_string(self.psycopg_uri(self.database_uri)) as saver:
            saver.setup()
            yield saver

    @staticmethod
    def safe_checkpoint_metadata(state: Any) -> dict[str, Any]:
        raw = asdict(state) if hasattr(state, "__dataclass_fields__") else dict(state)
        # Raw evidence text is intentionally absent from WorkflowState. Checkpoints hold
        # identifiers/findings; source evidence remains in immutable evidence-pack storage.
        return raw
