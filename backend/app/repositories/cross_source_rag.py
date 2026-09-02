from __future__ import annotations

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.db.session import set_tenant_context
from app.domain.cross_source_rag import FHIRQueryPlan, StructuredFact, StructuredQueryPlan
from app.models.claims import ClaimLineModel, ClaimModel, EncounterModel, PolicyModel, ProviderModel
from app.models.evidence_graph import CanonicalEntityModel, EvidenceContradictionModel, EvidenceGraphEdgeModel
from app.models.fhir import FHIRResourceSnapshotModel


class CrossSourceRepository:
    def __init__(self, session: Session, tenant_id: str) -> None:
        self.session = session
        self.tenant_id = tenant_id
        set_tenant_context(session, tenant_id)

    def claim(self, claim_id: str) -> ClaimModel | None:
        return self.session.scalar(select(ClaimModel).where(ClaimModel.tenant_id == self.tenant_id, ClaimModel.claim_id == claim_id))

    def structured_rows(self, plan: StructuredQueryPlan) -> dict[StructuredFact, list[object]]:
        claim = self.claim(plan.claim_id)
        if claim is None:
            return {}
        result: dict[StructuredFact, list[object]] = {}
        if StructuredFact.CLAIM in plan.facts:
            result[StructuredFact.CLAIM] = [claim]
        if StructuredFact.CLAIM_LINES in plan.facts:
            conditions = [ClaimLineModel.tenant_id == self.tenant_id, ClaimLineModel.claim_id == plan.claim_id]
            if plan.service_date_from:
                conditions.append(ClaimLineModel.service_date >= plan.service_date_from)
            if plan.service_date_to:
                conditions.append(ClaimLineModel.service_date <= plan.service_date_to)
            result[StructuredFact.CLAIM_LINES] = list(self.session.scalars(select(ClaimLineModel).where(and_(*conditions)).order_by(ClaimLineModel.line_number).limit(plan.max_rows)))
        if StructuredFact.POLICY in plan.facts and claim.policy_id:
            row = self.session.scalar(select(PolicyModel).where(PolicyModel.tenant_id == self.tenant_id, PolicyModel.policy_id == claim.policy_id))
            result[StructuredFact.POLICY] = [row] if row else []
        if StructuredFact.ENCOUNTER in plan.facts and claim.encounter_id:
            row = self.session.scalar(select(EncounterModel).where(EncounterModel.tenant_id == self.tenant_id, EncounterModel.encounter_id == claim.encounter_id))
            result[StructuredFact.ENCOUNTER] = [row] if row else []
        if StructuredFact.PROVIDER in plan.facts:
            result[StructuredFact.PROVIDER] = list(self.session.scalars(select(ProviderModel).where(ProviderModel.tenant_id == self.tenant_id, ProviderModel.organization_id == claim.provider_organization_id).limit(plan.max_rows)))
        if StructuredFact.CONTRADICTIONS in plan.facts:
            result[StructuredFact.CONTRADICTIONS] = self.open_contradictions(plan.claim_id, limit=plan.max_rows)
        return result

    def fhir_snapshots(self, plan: FHIRQueryPlan) -> list[FHIRResourceSnapshotModel]:
        return list(self.session.scalars(
            select(FHIRResourceSnapshotModel).where(
                FHIRResourceSnapshotModel.tenant_id == self.tenant_id,
                FHIRResourceSnapshotModel.claim_id == plan.claim_id,
                FHIRResourceSnapshotModel.resource_type.in_(plan.resource_types),
            ).order_by(FHIRResourceSnapshotModel.resource_type, FHIRResourceSnapshotModel.logical_id, FHIRResourceSnapshotModel.version_id.desc()).limit(plan.max_resources)
        ))

    def claim_entities(self, claim_id: str, *, limit: int = 50) -> list[CanonicalEntityModel]:
        return list(self.session.scalars(select(CanonicalEntityModel).where(CanonicalEntityModel.tenant_id == self.tenant_id, CanonicalEntityModel.claim_id == claim_id).limit(limit)))

    def graph_edges_for_claim(
        self,
        claim_id: str,
        *,
        relationship_types: tuple[str, ...] = (),
        as_of=None,
        max_edges: int = 100,
    ) -> list[EvidenceGraphEdgeModel]:
        conditions = [EvidenceGraphEdgeModel.tenant_id == self.tenant_id, EvidenceGraphEdgeModel.claim_id == claim_id]
        if relationship_types:
            conditions.append(EvidenceGraphEdgeModel.relationship_type.in_(relationship_types))
        if as_of:
            conditions.extend([
                or_(EvidenceGraphEdgeModel.valid_from.is_(None), EvidenceGraphEdgeModel.valid_from <= as_of),
                or_(EvidenceGraphEdgeModel.valid_to.is_(None), EvidenceGraphEdgeModel.valid_to >= as_of),
            ])
        return list(self.session.scalars(select(EvidenceGraphEdgeModel).where(and_(*conditions)).limit(max_edges)))

    def open_contradictions(self, claim_id: str, *, limit: int = 100) -> list[EvidenceContradictionModel]:
        return list(self.session.scalars(select(EvidenceContradictionModel).where(
            EvidenceContradictionModel.tenant_id == self.tenant_id,
            EvidenceContradictionModel.claim_id == claim_id,
            EvidenceContradictionModel.status == "open",
        ).order_by(EvidenceContradictionModel.severity.desc()).limit(limit)))

    def save_evidence_pack(self, pack, *, query_sha256: str, query_length: int, requested_retrievers: tuple[str, ...], trace_id: str | None = None) -> None:
        from datetime import datetime, timezone
        import uuid
        from app.models.cross_source_rag import EvidencePackContradictionModel, EvidencePackItemModel, EvidencePackModel
        model = EvidencePackModel(
            pack_id=pack.pack_id, tenant_id=self.tenant_id, claim_id=pack.claim_id,
            query_sha256=query_sha256, query_length=query_length, planner_version=pack.planner_version,
            requested_retrievers=list(requested_retrievers), executed_retrievers=[item.value for item in pack.executed_retrievers],
            evidence_count=len(pack.items), contradiction_count=len(pack.contradictions),
            confidence=pack.assessment.confidence, coverage=pack.assessment.coverage,
            source_diversity=pack.assessment.source_diversity, no_evidence=pack.assessment.no_evidence,
            unresolved_material_contradictions=pack.assessment.unresolved_material_contradictions,
            assessment_reasons=list(pack.assessment.reasons), trace_id=trace_id,
        )
        self.session.add(model)
        now = datetime.now(timezone.utc)
        for rank, item in enumerate(pack.items, start=1):
            self.session.add(EvidencePackItemModel(
                item_id=f"epitem_{uuid.uuid4().hex}", tenant_id=self.tenant_id, claim_id=pack.claim_id,
                pack_id=pack.pack_id, evidence_key=item.evidence_key, rank=rank, retriever=item.retriever.value,
                source_type=item.source_type, source_id=item.source_id, source_version=item.source_version,
                content_sha256=item.content_sha256, authority_rank=item.authority_rank, confidence=item.confidence,
                citation={
                    "source_type": item.citation.source_type, "source_id": item.citation.source_id,
                    "source_version": item.citation.source_version, "locator": item.citation.locator,
                    "entity_ids": list(item.citation.entity_ids), "relationship_path": list(item.citation.relationship_path),
                },
                metadata_summary=item.metadata, created_at=now,
            ))
        for contradiction in pack.contradictions:
            self.session.add(EvidencePackContradictionModel(
                item_id=f"epcon_{uuid.uuid4().hex}", tenant_id=self.tenant_id, claim_id=pack.claim_id,
                pack_id=pack.pack_id, contradiction_id=contradiction.contradiction_id,
                field_name=contradiction.field_name, severity=contradiction.severity,
                confidence=contradiction.confidence, status=contradiction.status, created_at=now,
            ))
        self.session.flush()
