from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from app.domain.rag import QueryPlan, RAGDomain

_SPACE_RE = re.compile(r"\s+")
_ISO_DATE_RE = re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b")
_CPT_RE = re.compile(r"\b\d{5}\b")
_ICD_RE = re.compile(r"\b[A-TV-Z][0-9][0-9A-Z](?:\.[0-9A-Z]{1,4})?\b", re.IGNORECASE)

_DOMAIN_TERMS: dict[RAGDomain, tuple[str, ...]] = {
    RAGDomain.POLICY: ("policy", "coverage", "covered", "benefit", "eligibility", "exclusion", "prior authorization", "preauthorization"),
    RAGDomain.HOSPITAL: ("hospital", "encounter", "fhir", "eob", "explanation of benefit", "practitioner", "clinical record"),
    RAGDomain.INVOICE: ("invoice", "bill", "billed", "charge", "amount", "receipt", "line item"),
    RAGDomain.CODING: ("cpt", "hcpcs", "icd", "snomed", "loinc", "coding", "code"),
    RAGDomain.HISTORICAL_CLAIMS: ("historical", "previous claim", "prior claim", "similar claim", "past claim", "duplicate"),
    RAGDomain.CLAIM: ("claim", "claim line", "submitted", "denial", "adjudication"),
    RAGDomain.EVIDENCE: ("document", "evidence", "upload", "attachment", "letter", "transcript", "image"),
}

_EXPANSIONS: tuple[tuple[str, str], ...] = (
    ("prior authorization", "preauthorization prior auth authorization requirement"),
    ("eob", "explanation of benefits"),
    ("coverage", "policy benefit eligibility covered service"),
    ("invoice", "bill billed charges line items"),
    ("denial", "denial reason rejected not covered"),
    ("duplicate", "duplicate prior historical claim"),
)


@dataclass(frozen=True)
class DeterministicQueryPlanner:
    version: str = "deterministic-healthcare-query-planner-v1"
    max_variants: int = 5
    max_subqueries: int = 4

    @staticmethod
    def normalize(query: str) -> str:
        return _SPACE_RE.sub(" ", query.strip())

    def plan(
        self,
        query: str,
        *,
        requested_domains: tuple[RAGDomain, ...] = (),
        service_date_from: date | None = None,
        service_date_to: date | None = None,
        minimum_authority_rank: int = 0,
    ) -> QueryPlan:
        normalized = self.normalize(query)
        if not normalized:
            raise ValueError("query cannot be empty")
        lowered = normalized.lower()

        inferred = tuple(
            domain for domain, terms in _DOMAIN_TERMS.items()
            if any(term in lowered for term in terms)
        )
        domains = requested_domains or inferred or tuple(RAGDomain)

        parsed_dates: list[date] = []
        for raw in _ISO_DATE_RE.findall(normalized):
            try:
                parsed_dates.append(date.fromisoformat(raw))
            except ValueError:
                continue
        temporal_from = service_date_from or (min(parsed_dates) if parsed_dates else None)
        temporal_to = service_date_to or (max(parsed_dates) if parsed_dates else None)

        codes = sorted({item.upper() for item in (*_CPT_RE.findall(normalized), *_ICD_RE.findall(normalized))})

        variants = [normalized]
        for needle, expansion in _EXPANSIONS:
            if needle in lowered:
                variants.append(f"{normalized} {expansion}")
        if codes:
            variants.append(" ".join(codes))
        # Preserve ordering while deduplicating.
        variants = list(dict.fromkeys(variants))[: self.max_variants]

        parts = re.split(r"\s+(?:and|versus|vs\.?|compare(?:d)?\s+with)\s+|[?;]", normalized, flags=re.IGNORECASE)
        subqueries = tuple(part.strip() for part in parts if len(part.strip()) >= 4)[: self.max_subqueries]
        if not subqueries:
            subqueries = (normalized,)

        exact_terms = tuple(codes)
        fallbacks = (
            "expand_to_all_authorized_domains_if_router_returns_zero_candidates",
            "dense_only_when_sparse_query_has_no_terms",
            "return_explicit_no_evidence_without_relaxing_tenant_claim_acl_or_temporal_scope",
        )
        return QueryPlan(
            original_query=query,
            normalized_query=normalized,
            variants=tuple(variants),
            subqueries=subqueries,
            domains=tuple(dict.fromkeys(domains)),
            exact_terms=exact_terms,
            service_date_from=temporal_from,
            service_date_to=temporal_to,
            minimum_authority_rank=max(0, min(100, minimum_authority_rank)),
            planner_version=self.version,
            fallbacks=fallbacks,
        )
