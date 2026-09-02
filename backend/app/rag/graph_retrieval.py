from __future__ import annotations

from collections import deque

from app.domain.cross_source_rag import EvidenceItem, GraphQueryPlan, RetrieverKind, UnifiedCitation, evidence_key
from app.repositories.cross_source_rag import CrossSourceRepository


class BoundedGraphRAGRetriever:
    """Claim-scoped deterministic graph traversal; no arbitrary Cypher/Gremlin/SQL generation."""

    def __init__(self, repository: CrossSourceRepository) -> None:
        self.repository = repository

    def retrieve(self, plan: GraphQueryPlan) -> tuple[EvidenceItem, ...]:
        entities = self.repository.claim_entities(plan.claim_id, limit=80)
        allowed = {row.entity_id: row for row in entities}
        if not allowed:
            return ()
        starts = list(plan.start_entity_ids) if plan.start_entity_ids else [
            row.entity_id for row in entities if row.entity_type == "claim"
        ]
        starts = [entity_id for entity_id in starts if entity_id in allowed]
        if not starts:
            starts = [next(iter(allowed))]
        edges = self.repository.graph_edges_for_claim(
            plan.claim_id, relationship_types=plan.relationship_types, as_of=plan.as_of,
            max_edges=plan.max_edges,
        )
        adjacency: dict[str, list[object]] = {}
        for edge in edges:
            if edge.source_entity_id in allowed and edge.target_entity_id in allowed:
                adjacency.setdefault(edge.source_entity_id, []).append(edge)
                adjacency.setdefault(edge.target_entity_id, []).append(edge)
        queue = deque((entity_id, 0, tuple()) for entity_id in starts)
        visited_edges: set[str] = set()
        visited_states: set[tuple[str, int]] = set()
        items: list[EvidenceItem] = []
        while queue and len(visited_edges) < plan.max_edges:
            entity_id, depth, path = queue.popleft()
            if depth >= plan.max_depth or (entity_id, depth) in visited_states:
                continue
            visited_states.add((entity_id, depth))
            for edge in adjacency.get(entity_id, []):
                if edge.edge_id in visited_edges:
                    continue
                visited_edges.add(edge.edge_id)
                other_id = edge.target_entity_id if edge.source_entity_id == entity_id else edge.source_entity_id
                other = allowed.get(other_id)
                current = allowed.get(entity_id)
                if not other or not current:
                    continue
                relationship_path = (*path, edge.relationship_type)
                text = f"Graph relationship: {current.entity_type}:{current.canonical_key} --{edge.relationship_type}--> {other.entity_type}:{other.canonical_key}."
                citation = UnifiedCitation(
                    source_type="evidence_graph", source_id=edge.edge_id,
                    entity_ids=(current.entity_id, other.entity_id), relationship_path=relationship_path,
                    locator={"edge_id": edge.edge_id},
                )
                items.append(EvidenceItem(
                    evidence_key=evidence_key("graph", edge.edge_id), retriever=RetrieverKind.GRAPH,
                    source_type="evidence_graph", source_id=edge.edge_id, text=text,
                    authority_rank=int(edge.authority_rank), confidence=float(edge.confidence), citation=citation,
                    metadata={"relationship_type": edge.relationship_type, "depth": depth + 1},
                ))
                queue.append((other_id, depth + 1, relationship_path))
        return tuple(items)
