from types import SimpleNamespace

from app.embeddings.batching import CachedBatchEmbedder
from app.embeddings.cache import MemoryEmbeddingCache
from app.embeddings.openai_provider import OpenAIEmbeddingProvider
from app.embeddings.provider import EmbeddingBatch, embedding_input_hash


class CountingProvider:
    model = "fake"
    dimensions = 3
    def __init__(self):
        self.calls = []
    def embed(self, texts):
        self.calls.append(list(texts))
        return EmbeddingBatch(
            vectors=[[float(len(text)), 1.0, 2.0] for text in texts],
            model=self.model,
            dimensions=self.dimensions,
            input_hashes=[embedding_input_hash(model=self.model, dimensions=self.dimensions, text=text) for text in texts],
        )


def test_cached_batch_embedder_batches_and_reuses_cache():
    provider = CountingProvider()
    embedder = CachedBatchEmbedder(provider, MemoryEmbeddingCache(), batch_size=2, ttl_seconds=60)
    first = embedder.embed(["a", "bb", "ccc"])
    second = embedder.embed(["a", "bb", "ccc"])
    assert len(provider.calls) == 2
    assert first == second


class FakeEmbeddings:
    def __init__(self): self.kwargs = None
    def create(self, **kwargs):
        self.kwargs = kwargs
        dims = kwargs["dimensions"]
        return SimpleNamespace(data=[SimpleNamespace(index=i, embedding=[float(i)] * dims) for i, _ in enumerate(kwargs["input"])])


class FakeClient:
    def __init__(self): self.embeddings = FakeEmbeddings()


def test_openai_adapter_forwards_model_dimensions_and_batch():
    client = FakeClient()
    provider = OpenAIEmbeddingProvider(model="text-embedding-3-large", dimensions=256, client=client)
    result = provider.embed(["first", "second"])
    assert result.dimensions == 256
    assert len(result.vectors) == 2
    assert client.embeddings.kwargs["model"] == "text-embedding-3-large"
    assert client.embeddings.kwargs["dimensions"] == 256
    assert client.embeddings.kwargs["encoding_format"] == "float"
