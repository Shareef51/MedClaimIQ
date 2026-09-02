from __future__ import annotations

from typing import Sequence

from app.embeddings.provider import EmbeddingBatch, embedding_input_hash
from app.observability.redaction import sha256_text
from app.observability.tracing import traced_operation
from app.observability.metrics import record_tokens


class OpenAIEmbeddingProvider:
    """OpenAI embeddings adapter. API keys are read by the official SDK/environment."""

    def __init__(self, *, model: str = "text-embedding-3-large", dimensions: int = 1536, client=None) -> None:
        if dimensions <= 0:
            raise ValueError("embedding dimensions must be positive")
        self.model = model
        self.dimensions = dimensions
        if client is None:
            from openai import OpenAI
            client = OpenAI()
        self._client = client

    def embed(self, texts: Sequence[str]) -> EmbeddingBatch:
        normalized = [text.replace("\n", " ").strip() for text in texts]
        if not normalized or any(not text for text in normalized):
            raise ValueError("embedding input cannot be empty")
        with traced_operation("openai.embeddings.create", kind="client", attributes={
            "model": self.model, "dimensions": self.dimensions, "batch_size": len(normalized),
            "batch_sha256": sha256_text("|".join(normalized)),
        }):
            response = self._client.embeddings.create(
                model=self.model,
                input=normalized,
                dimensions=self.dimensions,
                encoding_format="float",
            )
        usage=getattr(response,"usage",None)
        prompt_tokens=getattr(usage,"prompt_tokens",None) if usage else None
        if prompt_tokens is None and usage is not None: prompt_tokens=getattr(usage,"input_tokens",None)
        record_tokens(model=self.model,input_tokens=prompt_tokens,output_tokens=None)
        ordered = sorted(response.data, key=lambda item: item.index)
        vectors = [list(item.embedding) for item in ordered]
        if len(vectors) != len(normalized):
            raise RuntimeError("embedding provider returned a mismatched batch size")
        if any(len(vector) != self.dimensions for vector in vectors):
            raise RuntimeError("embedding provider returned unexpected vector dimensions")
        return EmbeddingBatch(
            vectors=vectors,
            model=self.model,
            dimensions=self.dimensions,
            input_hashes=[embedding_input_hash(model=self.model, dimensions=self.dimensions, text=text) for text in normalized],
        )
