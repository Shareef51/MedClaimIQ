from __future__ import annotations

import re
from dataclasses import replace
from typing import Sequence

from app.domain.rag import RetrievalHit

_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+|\n+")
_TERM_RE = re.compile(r"[a-z0-9]+(?:[.:-][a-z0-9]+)*", re.IGNORECASE)


class CitationWindowCompressor:
    version = "citation-window-compressor-v2"

    def __init__(self, *, max_chars_per_hit: int = 1800, max_sentences: int = 6) -> None:
        self.max_chars_per_hit = max_chars_per_hit
        self.max_sentences = max_sentences

    def compress(self, query: str, hits: Sequence[RetrievalHit]) -> list[RetrievalHit]:
        qterms = {m.group(0).lower() for m in _TERM_RE.finditer(query)}
        output: list[RetrievalHit] = []
        for hit in hits:
            if len(hit.text) <= self.max_chars_per_hit:
                output.append(hit)
                continue
            sentences = [s.strip() for s in _SENTENCE_RE.split(hit.text) if s.strip()]
            scored: list[tuple[int, int]] = []
            for index, sentence in enumerate(sentences):
                terms = {m.group(0).lower() for m in _TERM_RE.finditer(sentence)}
                score = len(qterms & terms)
                if score:
                    scored.append((score, index))
            anchors = sorted({index for _, index in sorted(scored, reverse=True)[: self.max_sentences]})
            if not anchors:
                anchors = list(range(min(self.max_sentences, len(sentences))))
            # Preserve original order and one-sentence neighborhood around strong matches.
            expanded = sorted({j for i in anchors for j in (i - 1, i, i + 1) if 0 <= j < len(sentences)})[: self.max_sentences + 2]
            text = " ".join(sentences[i] for i in expanded)[: self.max_chars_per_hit]
            metadata = dict(hit.metadata)
            metadata["context_compression"] = {
                "applied": True,
                "original_chars": len(hit.text),
                "returned_chars": len(text),
                "sentence_indexes": expanded,
                "citation_preserved": True,
                "version": self.version,
            }
            output.append(replace(hit, text=text, metadata=metadata))
        return output
