from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol, TypeVar

from pydantic import BaseModel
from app.observability.redaction import sha256_text
from app.observability.tracing import traced_operation

T = TypeVar("T", bound=BaseModel)


@dataclass(frozen=True, slots=True)
class StructuredModelResponse:
    parsed: BaseModel
    model: str
    response_id: str | None
    input_tokens: int | None = None
    output_tokens: int | None = None


class StructuredModelClient(Protocol):
    def generate(self, *, model: str, instructions: str, input_text: str, schema: type[T]) -> StructuredModelResponse: ...


class OpenAIResponsesStructuredClient:
    """OpenAI Responses API adapter using strict JSON Schema structured outputs."""

    def __init__(self, client=None) -> None:
        if client is None:
            try:
                from openai import OpenAI
            except ImportError as exc:  # pragma: no cover
                raise RuntimeError("openai package is required for production model calls") from exc
            client = OpenAI()
        self.client = client

    def generate(self, *, model: str, instructions: str, input_text: str, schema: type[T]) -> StructuredModelResponse:
        with traced_operation(
            "openai.responses.create", kind="client", attributes={
                "model": model, "schema": schema.__name__,
                "instructions_sha256": sha256_text(instructions),
                "input_sha256": sha256_text(input_text),
            },
        ):
            response = self.client.responses.create(
                model=model,
                instructions=instructions,
                input=input_text,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": schema.__name__,
                        "strict": True,
                        "schema": schema.model_json_schema(),
                    }
                },
            )
        raw = getattr(response, "output_text", "")
        if not raw:
            raise RuntimeError("model returned no structured output text")
        parsed = schema.model_validate(json.loads(raw))
        usage = getattr(response, "usage", None)
        return StructuredModelResponse(
            parsed=parsed,
            model=getattr(response, "model", model),
            response_id=getattr(response, "id", None),
            input_tokens=getattr(usage, "input_tokens", None) if usage else None,
            output_tokens=getattr(usage, "output_tokens", None) if usage else None,
        )
