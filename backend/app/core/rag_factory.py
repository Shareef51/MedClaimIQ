from __future__ import annotations

from app.core.config import Settings
from app.embeddings import CachedBatchEmbedder, OpenAIEmbeddingProvider, RedisEmbeddingCache
from app.vector import QdrantVectorStore


def build_cached_embedder(settings: Settings) -> CachedBatchEmbedder:
    import redis

    provider = OpenAIEmbeddingProvider(
        model=settings.rag_embedding_model,
        dimensions=settings.rag_embedding_dimensions,
    )
    cache = RedisEmbeddingCache(redis.Redis.from_url(settings.redis_url, decode_responses=True))
    return CachedBatchEmbedder(
        provider,
        cache,
        batch_size=settings.rag_embedding_batch_size,
        ttl_seconds=settings.rag_embedding_cache_ttl_seconds,
    )


def build_vector_store(settings: Settings) -> QdrantVectorStore:
    return QdrantVectorStore(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key.get_secret_value() if settings.qdrant_api_key else None,
        collection_prefix=settings.qdrant_collection_prefix,
        index_version=settings.rag_index_version,
        dimensions=settings.rag_embedding_dimensions,
        timeout_seconds=settings.qdrant_timeout_seconds,
    )
