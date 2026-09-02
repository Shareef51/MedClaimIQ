from __future__ import annotations

import json
from hashlib import sha256

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.evidence_tools import EvidenceSnapshot, EvidenceSnapshotItem
from app.domain.orchestration import EvidencePackBinding
from app.models.claims import ClaimLineModel, ClaimModel, EncounterModel, PolicyModel, ProviderModel
from app.models.cross_source_rag import (
    EvidencePackContradictionModel,
    EvidencePackItemModel,
    EvidencePackModel,
)
from app.models.evidence_graph import CanonicalEntityModel, EvidenceContradictionModel, EvidenceGraphEdgeModel
from app.models.fhir import FHIRResourceSnapshotModel
from app.models.rag import RAGChunkModel


class EvidenceHydrationError(RuntimeError):
    pass


class DatabaseEvidenceSnapshotProvider:
    """Rehydrate one immutable evidence-pack binding from authoritative source records.

    Evidence-pack rows intentionally store hashes/citations rather than duplicating all source
    text. Before an agent is allowed to reason, the source is reconstructed and compared with
    the content hash captured when the evidence pack was created. Source drift therefore fails
    closed instead of silently changing the evidence seen by a durable workflow.
    """

    def __init__(self, session: Session, tenant_id: str) -> None:
        self.session = session
        self.tenant_id = tenant_id

    def load(self, binding: EvidencePackBinding) -> EvidenceSnapshot:
        pack = self.session.scalar(
            select(EvidencePackModel).where(
                EvidencePackModel.tenant_id == self.tenant_id,
                EvidencePackModel.claim_id == binding.claim_id,
                EvidencePackModel.pack_id == binding.pack_id,
            )
        )
        if pack is None:
            raise EvidenceHydrationError("evidence pack not available in tenant/claim scope")
        pack_material = f"{pack.pack_id}|{pack.query_sha256}|{pack.evidence_count}|{pack.contradiction_count}|{pack.planner_version}"
        expected_binding_hash = sha256(pack_material.encode()).hexdigest()
        if binding.content_sha256 and binding.content_sha256 != expected_binding_hash:
            raise EvidenceHydrationError("evidence-pack binding hash no longer matches persisted pack metadata")

        items = list(
            self.session.scalars(
                select(EvidencePackItemModel)
                .where(
                    EvidencePackItemModel.tenant_id == self.tenant_id,
                    EvidencePackItemModel.claim_id == binding.claim_id,
                    EvidencePackItemModel.pack_id == binding.pack_id,
                )
                .order_by(EvidencePackItemModel.rank)
            )
        )
        hydrated = tuple(self._hydrate_item(row) for row in items)
        contradictions = tuple(self._hydrate_contradictions(binding))
        return EvidenceSnapshot(
            pack_id=pack.pack_id,
            claim_id=pack.claim_id,
            items=hydrated,
            contradictions=contradictions,
            assessment={
                "confidence": float(pack.confidence),
                "coverage": float(pack.coverage),
                "source_diversity": float(pack.source_diversity),
                "no_evidence": bool(pack.no_evidence),
                "unresolved_material_contradictions": int(pack.unresolved_material_contradictions),
                "reasons": list(pack.assessment_reasons or []),
            },
        )

    def _hydrate_item(self, row: EvidencePackItemModel) -> EvidenceSnapshotItem:
        text = self._resolve_text(row)
        actual = sha256(text.encode("utf-8")).hexdigest()
        if actual != row.content_sha256:
            raise EvidenceHydrationError(
                f"evidence source drift detected for {row.evidence_key}; create a new evidence pack"
            )
        return EvidenceSnapshotItem(
            evidence_key=row.evidence_key,
            text=text,
            source_type=row.source_type,
            source_id=row.source_id,
            source_version=row.source_version,
            authority_rank=int(row.authority_rank),
            confidence=float(row.confidence),
            citation=dict(row.citation or {}),
            metadata=dict(row.metadata_summary or {}),
        )

    def _resolve_text(self, row: EvidencePackItemModel) -> str:
        retriever = row.retriever
        if retriever == "sql":
            return self._structured_text(row.source_id)
        if retriever == "fhir":
            return self._fhir_text(row)
        if retriever == "graph":
            return self._graph_text(row.source_id)
        if retriever == "vector":
            return self._vector_text(row)
        raise EvidenceHydrationError(f"unsupported evidence retriever: {retriever}")

    def _structured_text(self, source_id: str) -> str:
        claim = self.session.scalar(
            select(ClaimModel).where(ClaimModel.tenant_id == self.tenant_id, ClaimModel.claim_id == source_id)
        )
        if claim is not None:
            return (
                f"Claim {claim.claim_id}: status={claim.status}; total={claim.total_amount} {claim.currency}; "
                f"service={claim.service_from} to {claim.service_to or claim.service_from}; "
                f"policy={claim.policy_id}; encounter={claim.encounter_id}."
            )
        line = self.session.scalar(
            select(ClaimLineModel).where(
                ClaimLineModel.tenant_id == self.tenant_id, ClaimLineModel.claim_line_id == source_id
            )
        )
        if line is not None:
            return (
                f"Claim line {line.line_number}: {line.code_system} {line.service_code}; "
                f"service_date={line.service_date}; units={line.units}; amount={line.amount}."
            )
        policy = self.session.scalar(
            select(PolicyModel).where(PolicyModel.tenant_id == self.tenant_id, PolicyModel.policy_id == source_id)
        )
        if policy is not None:
            return (
                f"Policy {policy.policy_id}: plan={policy.plan_name}; status={policy.status}; "
                f"effective={policy.effective_from} to {policy.effective_to or 'open'}; "
                f"version={policy.policy_version}."
            )
        encounter = self.session.scalar(
            select(EncounterModel).where(
                EncounterModel.tenant_id == self.tenant_id, EncounterModel.encounter_id == source_id
            )
        )
        if encounter is not None:
            return (
                f"Encounter {encounter.encounter_id}: type={encounter.encounter_type}; "
                f"started={encounter.started_at}; ended={encounter.ended_at}; "
                f"provider_org={encounter.provider_organization_id}."
            )
        provider = self.session.scalar(
            select(ProviderModel).where(
                ProviderModel.tenant_id == self.tenant_id, ProviderModel.provider_id == source_id
            )
        )
        if provider is not None:
            return (
                f"Provider {provider.provider_id}: ref={provider.provider_ref}; type={provider.provider_type}; "
                f"organization={provider.organization_id}; active={provider.is_active}."
            )
        raise EvidenceHydrationError(f"structured evidence source no longer exists: {source_id}")

    def _fhir_text(self, row: EvidencePackItemModel) -> str:
        snapshot_id = str((row.metadata_summary or {}).get("snapshot_id") or "")
        stmt = select(FHIRResourceSnapshotModel).where(
            FHIRResourceSnapshotModel.tenant_id == self.tenant_id,
            FHIRResourceSnapshotModel.claim_id == row.claim_id,
        )
        if snapshot_id:
            stmt = stmt.where(FHIRResourceSnapshotModel.snapshot_id == snapshot_id)
        else:
            resource_type, _, logical_id = row.source_id.partition("/")
            stmt = stmt.where(
                FHIRResourceSnapshotModel.resource_type == resource_type,
                FHIRResourceSnapshotModel.logical_id == logical_id,
                FHIRResourceSnapshotModel.version_id == (row.source_version or ""),
            )
        snapshot = self.session.scalar(stmt.limit(1))
        if snapshot is None:
            raise EvidenceHydrationError(f"FHIR evidence source no longer exists: {row.source_id}")
        text = json.dumps(snapshot.canonical_resource or {}, sort_keys=True, default=str, separators=(",", ":"))
        return text[:3500] + "…" if len(text) > 3500 else text

    def _graph_text(self, edge_id: str) -> str:
        edge = self.session.scalar(
            select(EvidenceGraphEdgeModel).where(
                EvidenceGraphEdgeModel.tenant_id == self.tenant_id,
                EvidenceGraphEdgeModel.edge_id == edge_id,
            )
        )
        if edge is None:
            raise EvidenceHydrationError(f"graph evidence source no longer exists: {edge_id}")
        entities = list(
            self.session.scalars(
                select(CanonicalEntityModel).where(
                    CanonicalEntityModel.tenant_id == self.tenant_id,
                    CanonicalEntityModel.entity_id.in_([edge.source_entity_id, edge.target_entity_id]),
                )
            )
        )
        by_id = {item.entity_id: item for item in entities}
        left, right = by_id.get(edge.source_entity_id), by_id.get(edge.target_entity_id)
        if left is None or right is None:
            raise EvidenceHydrationError(f"graph endpoints missing for edge: {edge_id}")
        return (
            f"Graph relationship: {left.entity_type}:{left.canonical_key} "
            f"--{edge.relationship_type}--> {right.entity_type}:{right.canonical_key}."
        )

    def _vector_text(self, row: EvidencePackItemModel) -> str:
        chunk_id = str((row.metadata_summary or {}).get("chunk_id") or "")
        if not chunk_id:
            raise EvidenceHydrationError("vector evidence pack item is missing chunk_id provenance")
        chunk = self.session.scalar(
            select(RAGChunkModel).where(
                RAGChunkModel.tenant_id == self.tenant_id,
                RAGChunkModel.claim_id == row.claim_id,
                RAGChunkModel.chunk_id == chunk_id,
                RAGChunkModel.active.is_(True),
            )
        )
        if chunk is None:
            raise EvidenceHydrationError(f"RAG chunk no longer exists: {chunk_id}")
        return chunk.content_text

    def _hydrate_contradictions(self, binding: EvidencePackBinding):
        rows = list(
            self.session.scalars(
                select(EvidencePackContradictionModel).where(
                    EvidencePackContradictionModel.tenant_id == self.tenant_id,
                    EvidencePackContradictionModel.claim_id == binding.claim_id,
                    EvidencePackContradictionModel.pack_id == binding.pack_id,
                )
            )
        )
        for row in rows:
            source = self.session.scalar(
                select(EvidenceContradictionModel).where(
                    EvidenceContradictionModel.tenant_id == self.tenant_id,
                    EvidenceContradictionModel.claim_id == binding.claim_id,
                    EvidenceContradictionModel.contradiction_id == row.contradiction_id,
                )
            )
            yield {
                "contradiction_id": row.contradiction_id,
                "field_name": row.field_name,
                "severity": row.severity,
                "confidence": float(row.confidence),
                "status": row.status,
                "left_value": dict(source.left_value) if source else {},
                "right_value": dict(source.right_value) if source else {},
            }
