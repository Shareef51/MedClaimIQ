from __future__ import annotations

from collections import deque
from datetime import date
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.models.evidence_graph import CanonicalEntityModel, EvidenceGraphEdgeModel


class EvidenceGraphRepository:
    def __init__(self, session: Session, tenant_id: str):
        self.session = session
        self.tenant_id = tenant_id

    def entity(self, entity_id: str) -> CanonicalEntityModel | None:
        return self.session.scalar(select(CanonicalEntityModel).where(CanonicalEntityModel.tenant_id == self.tenant_id, CanonicalEntityModel.entity_id == entity_id))

    def neighbors(self, entity_id: str, *, as_of: date | None = None, relationship_types: set[str] | None = None) -> list[EvidenceGraphEdgeModel]:
        conditions = [EvidenceGraphEdgeModel.tenant_id == self.tenant_id, or_(EvidenceGraphEdgeModel.source_entity_id == entity_id, EvidenceGraphEdgeModel.target_entity_id == entity_id)]
        if relationship_types:
            conditions.append(EvidenceGraphEdgeModel.relationship_type.in_(relationship_types))
        if as_of:
            conditions.extend([or_(EvidenceGraphEdgeModel.valid_from.is_(None), EvidenceGraphEdgeModel.valid_from <= as_of), or_(EvidenceGraphEdgeModel.valid_to.is_(None), EvidenceGraphEdgeModel.valid_to >= as_of)])
        return list(self.session.scalars(select(EvidenceGraphEdgeModel).where(and_(*conditions))))

    def traverse(self, start_entity_id: str, *, max_depth: int = 3, max_edges: int = 100, as_of: date | None = None) -> list[EvidenceGraphEdgeModel]:
        if max_depth < 1 or max_depth > 5:
            raise ValueError("max_depth must be between 1 and 5")
        queue: deque[tuple[str, int]] = deque([(start_entity_id, 0)])
        visited_entities = {start_entity_id}
        visited_edges: set[str] = set()
        result: list[EvidenceGraphEdgeModel] = []
        while queue and len(result) < max_edges:
            entity_id, depth = queue.popleft()
            if depth >= max_depth:
                continue
            for edge in self.neighbors(entity_id, as_of=as_of):
                if edge.edge_id in visited_edges:
                    continue
                visited_edges.add(edge.edge_id)
                result.append(edge)
                other = edge.target_entity_id if edge.source_entity_id == entity_id else edge.source_entity_id
                if other not in visited_entities:
                    visited_entities.add(other)
                    queue.append((other, depth + 1))
                if len(result) >= max_edges:
                    break
        return result
