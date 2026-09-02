from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import UTC, datetime
from time import perf_counter
from typing import Any

from app.domain.advanced_rag import Answerability
from app.domain.multimodal_rag import (
    EvidenceModality,
    MultimodalCandidate,
    MultimodalCitation,
    MultimodalEvidencePack,
    MultimodalRAGResult,
)
from app.domain.orchestration import AgentName
from app.domain.rag import RAGDomain, RetrievalScope
from app.models.multimodal_rag import MultimodalEvidencePackModel, MultimodalInconsistencyModel, MultimodalRAGItemModel, MultimodalRAGRunModel
from app.rag.multimodal_fusion import ModalityAwareReranker
from app.rag.multimodal_gap import MultimodalGapDetector
from app.rag.multimodal_routing import MultimodalRouter
from app.rag.multimodal_verification import CrossModalVerifier
from app.repositories.multimodal_rag import ExtractionSourceUnit, MultimodalRAGRepository

_TOKEN = re.compile(r"[a-z0-9]{2,}", re.I)


class MultimodalRAGService:
    def __init__(
        self,
        *,
        repository: MultimodalRAGRepository,
        text_retriever: Any | None = None,
        router: MultimodalRouter | None = None,
        reranker: ModalityAwareReranker | None = None,
        verifier: CrossModalVerifier | None = None,
        gap_detector: MultimodalGapDetector | None = None,
        max_candidates: int = 60,
    ) -> None:
        self.repository = repository
        self.text_retriever = text_retriever
        self.router = router or MultimodalRouter()
        self.reranker = reranker or ModalityAwareReranker()
        self.verifier = verifier or CrossModalVerifier()
        self.gap_detector = gap_detector or MultimodalGapDetector()
        self.max_candidates = max(10, min(200, max_candidates))

    def plan_only(self, *, query: str, requested_modalities=(), required_modalities=(), agent: AgentName | None = None):
        return self.router.plan(query, requested_modalities=tuple(requested_modalities), required_modalities=tuple(required_modalities), agent=agent)

    def search(
        self,
        *,
        query: str,
        scope: RetrievalScope,
        agent: AgentName | None = None,
        requested_modalities: tuple[EvidenceModality, ...] = (),
        required_modalities: tuple[EvidenceModality, ...] = (),
        limit: int = 12,
        trace_id: str | None = None,
    ) -> MultimodalRAGResult:
        if not query.strip():
            raise ValueError("query cannot be empty")
        if not scope.claim_id:
            raise ValueError("multimodal RAG requires claim scope")
        if scope.tenant_id != self.repository.tenant_id:
            raise PermissionError("cross-tenant multimodal RAG retrieval denied")
        if limit <= 0:
            raise ValueError("limit must be positive")

        started = perf_counter()
        route = self.router.plan(query, requested_modalities=requested_modalities, required_modalities=required_modalities, agent=agent)
        candidates: list[MultimodalCandidate] = []

        if EvidenceModality.TEXT in route.modalities and self.text_retriever is not None:
            advanced = self.text_retriever.search(query=query, scope=scope, agent=agent, limit=min(limit, 8), trace_id=trace_id)
            for hit in advanced.hits:
                candidates.append(self._from_text_hit(hit))

        units = self.repository.extraction_units(claim_id=scope.claim_id)
        for source in units:
            item = self._from_extraction_unit(source, query=query)
            if item is not None and item.modality in route.modalities:
                candidates.append(item)

        if EvidenceModality.FHIR in route.modalities:
            for snapshot in self.repository.fhir_snapshots(claim_id=scope.claim_id):
                candidates.append(self._from_fhir(snapshot, query=query))

        # Bound before reranking to keep adversarially large extraction manifests from amplifying work.
        candidates = sorted(candidates, key=lambda x: (-x.score, x.item_id))[: self.max_candidates]
        selected = self.reranker.rerank(query, candidates, limit=min(30, limit))
        inconsistencies = self.verifier.verify(selected)
        gaps, answerability, modality_coverage, citation_coverage = self.gap_detector.detect(route=route, items=selected, inconsistencies=inconsistencies)
        confidence = round(sum(item.confidence * item.score for item in selected) / max(1, sum(item.score for item in selected)), 6) if selected else 0.0
        source_diversity = round(len({(x.source_id, x.source_version) for x in selected}) / len(selected), 6) if selected else 0.0
        run_id = f"mmrag_{uuid.uuid4().hex}"
        pack_id = f"mmep_{uuid.uuid4().hex}"
        pack = MultimodalEvidencePack(
            pack_id=pack_id,
            run_id=run_id,
            claim_id=scope.claim_id,
            items=tuple(selected),
            inconsistencies=inconsistencies,
            gaps=gaps,
            answerability=answerability,
            confidence=confidence,
            modality_coverage=modality_coverage,
            citation_coverage=citation_coverage,
            source_diversity=source_diversity,
            diagnostics={
                "candidate_count": len(candidates),
                "routed_modalities": [m.value for m in route.modalities],
                "raw_media_persisted_in_telemetry": False,
                "human_review_required": answerability != Answerability.ANSWERABLE or bool(inconsistencies),
            },
        )
        result = MultimodalRAGResult(run_id=run_id, query=query, route=route, pack=pack, latency_ms=max(0, int((perf_counter()-started)*1000)), trace_id=trace_id)
        self._persist(result, scope=scope, requested_modalities=requested_modalities)
        return result

    def _from_text_hit(self, hit) -> MultimodalCandidate:
        citation = hit.citation or {}
        return MultimodalCandidate(
            item_id=f"text:{hit.chunk_id}", modality=EvidenceModality.TEXT, domain=hit.domain,
            source_id=str(hit.metadata.get("source_id") or hit.chunk_id), source_version=str(hit.metadata.get("source_version") or ""),
            text=hit.text, score=float(hit.rerank_score or hit.score), confidence=float(hit.metadata.get("evidence_confidence", 0.75)),
            authority_rank=int(hit.metadata.get("authority_rank", 60)),
            citation=MultimodalCitation(
                modality=EvidenceModality.TEXT, evidence_id=citation.get("evidence_id"), extraction_unit_id=citation.get("extraction_unit_id"),
                page_number=citation.get("page_number"), bbox=tuple(citation["bbox"]) if citation.get("bbox") else None,
                start_ms=citation.get("start_ms"), end_ms=citation.get("end_ms"), source_locator=dict(citation.get("source_locator") or {}),
            ),
            metadata={"chunk_id": hit.chunk_id, "parent_chunk_id": hit.parent_chunk_id}, retrieval_sources=tuple(hit.retrieval_sources),
        )

    def _from_extraction_unit(self, source: ExtractionSourceUnit, *, query: str) -> MultimodalCandidate | None:
        unit = source.unit
        modality = self._unit_modality(str(unit.unit_type), source.media_type)
        text = str(unit.text_content or "").strip()
        structured = dict(unit.structured_data or {})
        if not text and structured:
            text = json.dumps(structured, sort_keys=True, separators=(",", ":"), default=str)
        if not text:
            return None
        overlap = self._overlap(query, text)
        locator = dict(unit.source_locator or {})
        frame_index = self._safe_int(locator.get("frame_index"))
        frame_sha = str(locator.get("frame_sha256") or structured.get("frame_sha256") or "") or None
        if str(unit.unit_type) == "video_keyframe":
            locator.setdefault("kind", "keyframe")
        citation = MultimodalCitation(
            modality=modality, evidence_id=unit.source_evidence_id, extraction_unit_id=unit.unit_id,
            page_number=unit.page_number, bbox=tuple(float(x) for x in unit.bbox) if unit.bbox else None,
            start_ms=unit.start_ms, end_ms=unit.end_ms, frame_index=frame_index, frame_sha256=frame_sha, source_locator=locator,
        )
        domain = self._domain_for(modality, source.media_type, structured)
        confidence = float(unit.confidence)
        return MultimodalCandidate(
            item_id=f"unit:{unit.unit_id}", modality=modality, domain=domain, source_id=unit.source_evidence_id,
            source_version=source.source_version, text=text[:12000], score=round(0.35 + 0.45*overlap + 0.20*confidence, 6),
            confidence=confidence, authority_rank=65, citation=citation,
            metadata={"unit_type": str(unit.unit_type), "media_type": source.media_type, "structured_keys": sorted(structured)[:30]},
            retrieval_sources=("extraction-unit", modality.value),
        )

    def _from_fhir(self, snapshot, *, query: str) -> MultimodalCandidate:
        canonical = snapshot.canonical_resource or snapshot.raw_resource or {}
        text = json.dumps(canonical, sort_keys=True, separators=(",", ":"), default=str)
        overlap = self._overlap(query, text)
        return MultimodalCandidate(
            item_id=f"fhir:{snapshot.snapshot_id}", modality=EvidenceModality.FHIR, domain=RAGDomain.HOSPITAL,
            source_id=f"{snapshot.resource_type}/{snapshot.logical_id}", source_version=snapshot.version_id,
            text=text[:12000], score=round(0.45 + 0.35*overlap + (0.15 if snapshot.authoritative else 0), 6),
            confidence=0.95 if snapshot.authoritative else 0.70, authority_rank=95 if snapshot.authoritative else 70,
            citation=MultimodalCitation(
                modality=EvidenceModality.FHIR, fhir_snapshot_id=snapshot.snapshot_id, fhir_resource_type=snapshot.resource_type,
                fhir_logical_id=snapshot.logical_id, fhir_version_id=snapshot.version_id,
                source_locator={"source_url_sha256": hashlib.sha256(snapshot.source_url.encode()).hexdigest()},
            ),
            metadata={"resource_type": snapshot.resource_type, "authoritative": bool(snapshot.authoritative), "content_sha256": snapshot.content_sha256},
            retrieval_sources=("fhir-snapshot",),
        )

    @staticmethod
    def _unit_modality(unit_type: str, media_type: str) -> EvidenceModality:
        if unit_type == "table": return EvidenceModality.TABLE
        if unit_type == "video_keyframe": return EvidenceModality.VIDEO
        if unit_type == "audio_segment": return EvidenceModality.VIDEO if media_type.startswith("video/") else EvidenceModality.AUDIO
        if media_type.startswith("image/"): return EvidenceModality.IMAGE
        if media_type.startswith("audio/"): return EvidenceModality.AUDIO
        if media_type.startswith("video/"): return EvidenceModality.VIDEO
        return EvidenceModality.DOCUMENT

    @staticmethod
    def _domain_for(modality: EvidenceModality, media_type: str, structured: dict) -> RAGDomain:
        hay = f"{media_type} {structured.get('document_type','')}".lower()
        if "invoice" in hay or "bill" in hay or modality == EvidenceModality.TABLE: return RAGDomain.INVOICE
        return RAGDomain.EVIDENCE

    @staticmethod
    def _overlap(query: str, text: str) -> float:
        q=set(_TOKEN.findall(query.lower())); t=set(_TOKEN.findall(text.lower()))
        return len(q & t)/len(q) if q else 0.0

    @staticmethod
    def _safe_int(value):
        try: return int(value) if value is not None else None
        except (TypeError, ValueError): return None

    def _persist(self, result: MultimodalRAGResult, *, scope: RetrievalScope, requested_modalities) -> None:
        now = datetime.now(UTC)
        pack = result.pack
        payload = [{"item_id": i.item_id, "source_id": i.source_id, "source_version": i.source_version, "modality": i.modality.value, "citation": i.citation.as_dict()} for i in pack.items]
        pack_sha = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()
        run_model = MultimodalRAGRunModel(
            run_id=result.run_id, tenant_id=scope.tenant_id, claim_id=scope.claim_id or "",
            query_sha256=hashlib.sha256(result.query.encode()).hexdigest(), query_length=len(result.query),
            agent_name=result.route.agent.value if result.route.agent else None, intent=result.route.intent.value,
            requested_modalities=[m.value for m in requested_modalities], routed_modalities=[m.value for m in result.route.modalities],
            required_modalities=[m.value for m in result.route.required_modalities], selected_count=len(pack.items),
            confidence=pack.confidence, modality_coverage=pack.modality_coverage, citation_coverage=pack.citation_coverage,
            source_diversity=pack.source_diversity, inconsistency_count=len(pack.inconsistencies), knowledge_gap_count=len(pack.gaps),
            answerability=pack.answerability.value, planner_version=result.route.planner_version, reranker_version=self.reranker.version,
            verifier_version=self.verifier.version, latency_ms=result.latency_ms, trace_id=result.trace_id,
        )
        pack_model = MultimodalEvidencePackModel(
            pack_id=pack.pack_id, tenant_id=scope.tenant_id, claim_id=scope.claim_id or "", run_id=result.run_id,
            item_count=len(pack.items), modalities=sorted({x.modality.value for x in pack.items}), confidence=pack.confidence,
            modality_coverage=pack.modality_coverage, citation_coverage=pack.citation_coverage, answerability=pack.answerability.value,
            pack_sha256=pack_sha, created_at=now,
        )
        item_models=[]
        for rank,item in enumerate(pack.items,1):
            item_models.append(MultimodalRAGItemModel(
                item_event_id=f"mmri_{uuid.uuid4().hex}", tenant_id=scope.tenant_id, claim_id=scope.claim_id or "", run_id=result.run_id, pack_id=pack.pack_id,
                item_id=item.item_id, modality=item.modality.value, domain=item.domain.value, source_id=item.source_id, source_version=item.source_version,
                content_sha256=hashlib.sha256(item.text.encode()).hexdigest(), rank=rank, score=item.score, confidence=item.confidence,
                authority_rank=item.authority_rank, citation=item.citation.as_dict(),
                metadata_summary={"keys": sorted(item.metadata)[:30]}, retrieval_sources=list(item.retrieval_sources), created_at=now,
            ))
        inconsistency_models=[]
        for inc in pack.inconsistencies:
            inconsistency_models.append(MultimodalInconsistencyModel(
                inconsistency_id=f"mmi_{uuid.uuid4().hex}", tenant_id=scope.tenant_id, claim_id=scope.claim_id or "", run_id=result.run_id, pack_id=pack.pack_id,
                code=inc.code, field=inc.field, severity=inc.severity.value, left_item_id=inc.left_item_id, right_item_id=inc.right_item_id,
                left_value_sha256=hashlib.sha256(inc.left_value.encode()).hexdigest(), right_value_sha256=hashlib.sha256(inc.right_value.encode()).hexdigest(),
                confidence=inc.confidence, human_review_required=True, created_at=now,
            ))
        self.repository.add_result(run=run_model, pack=pack_model, items=item_models, inconsistencies=inconsistency_models)
