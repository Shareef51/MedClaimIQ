from __future__ import annotations

from dataclasses import replace
from typing import Sequence

from app.domain.rag import RetrievalHit


def reciprocal_rank_fusion(
    ranked_lists: Sequence[Sequence[RetrievalHit]],
    *,
    k: int = 60,
) -> list[RetrievalHit]:
    if k <= 0:
        raise ValueError("RRF k must be positive")
    fused: dict[str, dict[str, object]] = {}
    for result_list in ranked_lists:
        for rank, hit in enumerate(result_list, start=1):
            state = fused.setdefault(
                hit.chunk_id,
                {"hit": hit, "rrf": 0.0, "dense": None, "sparse": None, "sources": set()},
            )
            state["rrf"] = float(state["rrf"]) + 1.0 / (k + rank)
            sources = state["sources"]
            assert isinstance(sources, set)
            sources.update(hit.retrieval_sources)
            if hit.dense_score is not None:
                previous = state["dense"]
                state["dense"] = hit.dense_score if previous is None else max(float(previous), hit.dense_score)
            if hit.sparse_score is not None:
                previous = state["sparse"]
                state["sparse"] = hit.sparse_score if previous is None else max(float(previous), hit.sparse_score)

    output: list[RetrievalHit] = []
    for state in fused.values():
        hit = state["hit"]
        assert isinstance(hit, RetrievalHit)
        output.append(
            replace(
                hit,
                dense_score=float(state["dense"]) if state["dense"] is not None else None,
                sparse_score=float(state["sparse"]) if state["sparse"] is not None else None,
                fused_score=float(state["rrf"]),
                score=float(state["rrf"]),
                retrieval_sources=tuple(sorted(state["sources"])),
            )
        )
    output.sort(key=lambda item: item.fused_score or 0.0, reverse=True)
    return output
