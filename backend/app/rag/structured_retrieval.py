from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.domain.cross_source_rag import EvidenceItem, RetrieverKind, StructuredFact, StructuredQueryPlan, UnifiedCitation, evidence_key
from app.domain.evidence_graph import authority_rank
from app.repositories.cross_source_rag import CrossSourceRepository


def _value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    return value


class StructuredSQLRetriever:
    """Executes only whitelisted SQLAlchemy query templates represented by StructuredQueryPlan."""

    def __init__(self, repository: CrossSourceRepository) -> None:
        self.repository = repository

    def retrieve(self, plan: StructuredQueryPlan) -> tuple[EvidenceItem, ...]:
        rows = self.repository.structured_rows(plan)
        items: list[EvidenceItem] = []
        for fact, fact_rows in rows.items():
            for row in fact_rows:
                if fact is StructuredFact.CLAIM:
                    text = f"Claim {row.claim_id}: status={row.status}; total={row.total_amount} {row.currency}; service={row.service_from} to {row.service_to or row.service_from}; policy={row.policy_id}; encounter={row.encounter_id}."
                    sid, confidence = row.claim_id, 0.98
                elif fact is StructuredFact.CLAIM_LINES:
                    text = f"Claim line {row.line_number}: {row.code_system} {row.service_code}; service_date={row.service_date}; units={row.units}; amount={row.amount}."
                    sid, confidence = row.claim_line_id, 0.98
                elif fact is StructuredFact.POLICY:
                    text = f"Policy {row.policy_id}: plan={row.plan_name}; status={row.status}; effective={row.effective_from} to {row.effective_to or 'open'}; version={row.policy_version}."
                    sid, confidence = row.policy_id, 0.97
                elif fact is StructuredFact.ENCOUNTER:
                    text = f"Encounter {row.encounter_id}: type={row.encounter_type}; started={row.started_at}; ended={row.ended_at}; provider_org={row.provider_organization_id}."
                    sid, confidence = row.encounter_id, 0.97
                elif fact is StructuredFact.PROVIDER:
                    text = f"Provider {row.provider_id}: ref={row.provider_ref}; type={row.provider_type}; organization={row.organization_id}; active={row.is_active}."
                    sid, confidence = row.provider_id, 0.96
                else:
                    # Contradictions are fused separately and are not duplicated as fact text.
                    continue
                citation = UnifiedCitation(source_type="structured_claim_db", source_id=str(sid), source_version="1")
                items.append(EvidenceItem(
                    evidence_key=evidence_key("sql", fact.value, sid), retriever=RetrieverKind.SQL,
                    source_type="structured_claim_db", source_id=str(sid), text=text,
                    authority_rank=authority_rank("structured_claim_db"), confidence=confidence, citation=citation,
                    source_version="1", metadata={"fact": fact.value, "claim_id": plan.claim_id},
                ))
        return tuple(items)
