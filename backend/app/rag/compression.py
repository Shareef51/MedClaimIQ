from __future__ import annotations

import re
from dataclasses import replace
from typing import Sequence

from app.domain.rag import RetrievalHit

_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+|\n+")
_TERM_RE = re.compile(r"[a-z0-9]+(?:[.:-][a-z0-9]+)*", re.IGNORECASE)


class ContextualCompressor:
    version = "citation-safe-context-compressor-v1"

    def __init__(self, *, max_chars_per_hit: int = 2400, max_sentences: int = 8) -> None:
        self.max_chars_per_hit = max_chars_per_hit
        self.max_sentences = max_sentences

    def compress(self, query: str, hits: Sequence[RetrievalHit]) -> list[RetrievalHit]:
        qterms = {m.group(0).lower() for m in _TERM_RE.finditer(query)}
        output: list[RetrievalHit] = []
        for hit in hits:
            if len(hit.text) <= self.max_chars_per_hit:
                output.append(hit)
                continue
            sentences = [part.strip() for part in _SENTENCE_RE.split(hit.text) if part.strip()]
            ranked: list[tuple[int, int, str]] = []
            for index, sentence in enumerate(sentences):
                terms = {m.group(0).lower() for m in _TERM_RE.finditer(sentence)}
                ranked.append((len(qterms & terms), -index, sentence))
            ranked.sort(reverse=True)
            chosen = [item[2] for item in ranked[: self.max_sentences] if item[0] > 0]
            if not chosen:
                chosen = sentences[: self.max_sentences]
            text = " ".join(chosen)[: self.max_chars_per_hit]
            metadata = dict(hit.metadata)
            metadata["context_compression"] = {
                "applied": True,
                "original_chars": len(hit.text),
                "returned_chars": len(text),
                "version": self.version,
            }
            output.append(replace(hit, text=text, metadata=metadata))
        return output
