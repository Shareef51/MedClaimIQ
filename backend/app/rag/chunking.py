from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime, time
from dataclasses import replace
from typing import Iterable

from app.domain.rag import ChunkKind, KnowledgeDocument, RAGChunk, SourceSegment

_TOKEN_RE = re.compile(r"\S+")


def estimate_tokens(text: str) -> int:
    # Deterministic, dependency-light estimate for chunk planning. The embedding API
    # remains the final authority on request limits.
    words = len(_TOKEN_RE.findall(text))
    return max(1, int(words * 1.35)) if text.strip() else 0


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:32]
    return f"{prefix}_{digest}"


def _word_windows(text: str, target_tokens: int, overlap_tokens: int) -> Iterable[str]:
    words = text.split()
    if not words:
        return
    target_words = max(20, int(target_tokens / 1.35))
    overlap_words = max(0, min(target_words // 2, int(overlap_tokens / 1.35)))
    start = 0
    while start < len(words):
        end = min(len(words), start + target_words)
        yield " ".join(words[start:end])
        if end >= len(words):
            break
        start = max(start + 1, end - overlap_words)


class ParentChildChunker:
    def __init__(self, *, parent_tokens: int = 1200, child_tokens: int = 350, overlap_tokens: int = 60) -> None:
        if not 100 <= child_tokens < parent_tokens:
            raise ValueError("child_tokens must be smaller than parent_tokens")
        if overlap_tokens >= child_tokens:
            raise ValueError("overlap_tokens must be smaller than child_tokens")
        self.parent_tokens = parent_tokens
        self.child_tokens = child_tokens
        self.overlap_tokens = overlap_tokens

    def chunk(self, document: KnowledgeDocument) -> list[RAGChunk]:
        chunks: list[RAGChunk] = []
        ordinal = 0
        for segment in document.segments:
            if not segment.text or not segment.text.strip():
                continue
            citation = segment.citation.as_payload() if segment.citation else {}
            kind = self._kind_for(segment)
            parent_texts = list(_word_windows(segment.text, self.parent_tokens, 0))
            for parent_index, parent_text in enumerate(parent_texts):
                parent_id = _stable_id(
                    "ragp", document.tenant_id, document.domain.value, document.source_id,
                    document.source_version, segment.segment_id, str(parent_index), _sha256(parent_text),
                )
                parent_metadata = self._metadata(document, segment, parent_id=None)
                chunks.append(
                    RAGChunk(
                        chunk_id=parent_id,
                        tenant_id=document.tenant_id,
                        claim_id=document.claim_id,
                        patient_subject_id=document.patient_subject_id,
                        domain=document.domain,
                        source_type=document.source_type,
                        source_id=document.source_id,
                        source_version=document.source_version,
                        parent_chunk_id=None,
                        kind=ChunkKind.PARENT,
                        ordinal=ordinal,
                        text=parent_text,
                        content_sha256=_sha256(parent_text),
                        token_count=estimate_tokens(parent_text),
                        citation=citation,
                        metadata=parent_metadata,
                    )
                )
                ordinal += 1
                # Tables/transcript segments still get child chunks, but retain their semantic kind in metadata.
                child_texts = list(_word_windows(parent_text, self.child_tokens, self.overlap_tokens))
                for child_index, child_text in enumerate(child_texts):
                    child_id = _stable_id(
                        "ragc", document.tenant_id, document.domain.value, document.source_id,
                        document.source_version, parent_id, str(child_index), _sha256(child_text),
                    )
                    chunks.append(
                        RAGChunk(
                            chunk_id=child_id,
                            tenant_id=document.tenant_id,
                            claim_id=document.claim_id,
                            patient_subject_id=document.patient_subject_id,
                            domain=document.domain,
                            source_type=document.source_type,
                            source_id=document.source_id,
                            source_version=document.source_version,
                            parent_chunk_id=parent_id,
                            kind=kind,
                            ordinal=ordinal,
                            text=child_text,
                            content_sha256=_sha256(child_text),
                            token_count=estimate_tokens(child_text),
                            citation=citation,
                            metadata=self._metadata(document, segment, parent_id=parent_id),
                        )
                    )
                    ordinal += 1
        return chunks

    @staticmethod
    def _kind_for(segment: SourceSegment) -> ChunkKind:
        lowered = segment.unit_type.lower()
        if "table" in lowered:
            return ChunkKind.TABLE
        if lowered in {"transcript", "audio_transcript", "video_transcript"}:
            return ChunkKind.TRANSCRIPT
        return ChunkKind.CHILD

    @staticmethod
    def _metadata(document: KnowledgeDocument, segment: SourceSegment, parent_id: str | None) -> dict[str, object]:
        return {
            "tenant_id": document.tenant_id,
            "claim_id": document.claim_id,
            "patient_subject_id": document.patient_subject_id,
            "domain": document.domain.value,
            "source_type": document.source_type,
            "source_id": document.source_id,
            "source_version": document.source_version,
            "source_content_sha256": document.source_content_sha256,
            "authority_rank": document.authority_rank,
            "evidence_confidence": document.evidence_confidence,
            "entity_ids": sorted(set(document.entity_ids)),
            "relationship_types": sorted(set(document.relationship_types)),
            "acl_tags": sorted(set(document.acl_tags)),
            "service_date": datetime.combine(document.service_date, time.min, tzinfo=UTC).isoformat().replace("+00:00", "Z") if document.service_date else None,
            "segment_id": segment.segment_id,
            "segment_type": segment.unit_type,
            "parent_chunk_id": parent_id,
            "structured_data": segment.structured_data,
            **document.attributes,
        }
