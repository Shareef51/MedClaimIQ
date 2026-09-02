from __future__ import annotations

from app.domain.advanced_rag import AgentRetrievalDirective
from app.domain.orchestration import AgentName
from app.domain.rag import RAGDomain, RetrievalScope


_AGENT_DOMAINS: dict[AgentName, tuple[RAGDomain, ...]] = {
    AgentName.INTAKE: (RAGDomain.CLAIM, RAGDomain.EVIDENCE),
    AgentName.HOSPITAL_VERIFICATION: (RAGDomain.HOSPITAL, RAGDomain.CLAIM, RAGDomain.EVIDENCE),
    AgentName.INVOICE_VERIFICATION: (RAGDomain.INVOICE, RAGDomain.CLAIM, RAGDomain.EVIDENCE),
    AgentName.ELIGIBILITY: (RAGDomain.POLICY, RAGDomain.HOSPITAL, RAGDomain.CLAIM),
    AgentName.POLICY: (RAGDomain.POLICY, RAGDomain.CLAIM),
    AgentName.CODING: (RAGDomain.CODING, RAGDomain.HOSPITAL, RAGDomain.INVOICE),
    AgentName.DUPLICATE_CLAIM: (RAGDomain.HISTORICAL_CLAIMS, RAGDomain.CLAIM),
    AgentName.FRAUD_WASTE: (RAGDomain.HISTORICAL_CLAIMS, RAGDomain.INVOICE, RAGDomain.EVIDENCE),
    AgentName.DENIAL_RISK: (RAGDomain.POLICY, RAGDomain.CODING, RAGDomain.CLAIM, RAGDomain.EVIDENCE),
    AgentName.EVIDENCE_FUSION: tuple(RAGDomain),
    AgentName.CRITIC: tuple(RAGDomain),
    AgentName.DECISION_SUPPORT: tuple(RAGDomain),
    AgentName.HUMAN_REVIEW_ROUTER: tuple(RAGDomain),
}

_AGENT_EVIDENCE: dict[AgentName, tuple[str, ...]] = {
    AgentName.HOSPITAL_VERIFICATION: ("FHIR resource", "hospital record", "claim evidence"),
    AgentName.INVOICE_VERIFICATION: ("invoice", "claim line", "provider evidence"),
    AgentName.ELIGIBILITY: ("coverage", "policy version", "service date"),
    AgentName.POLICY: ("policy clause", "effective date", "citation"),
    AgentName.CODING: ("code evidence", "claim line", "source version"),
    AgentName.DUPLICATE_CLAIM: ("historical claim", "claim identifiers"),
    AgentName.CRITIC: ("primary evidence", "contradictions", "citations"),
    AgentName.DECISION_SUPPORT: ("evidence pack", "policy", "verification findings"),
}


class AgentDirectedRetrievalPlanner:
    version = "agent-directed-retrieval-v1"

    def plan(self, *, agent: AgentName | None, scope: RetrievalScope) -> AgentRetrievalDirective:
        authorized = tuple(scope.domains or tuple(RAGDomain))
        if agent is None:
            domains = authorized
            minimum_authority = scope.minimum_authority_rank
            max_rounds = 1
            required = ("citation", "source version")
            reasons = ("interactive_reviewer_query",)
        else:
            preferred = _AGENT_DOMAINS.get(agent, tuple(RAGDomain))
            domains = tuple(d for d in preferred if d in set(authorized)) or authorized
            minimum_authority = max(scope.minimum_authority_rank, 60 if agent in {AgentName.POLICY, AgentName.CODING, AgentName.DECISION_SUPPORT} else 40)
            max_rounds = 2 if agent in {AgentName.CRITIC, AgentName.EVIDENCE_FUSION, AgentName.DECISION_SUPPORT} else 1
            required = _AGENT_EVIDENCE.get(agent, ("source evidence", "citation"))
            reasons = (f"agent_profile:{agent.value}", "domains_intersected_with_authorized_scope")
        return AgentRetrievalDirective(
            agent=agent,
            domains=domains,
            required_evidence_types=required,
            minimum_authority_rank=minimum_authority,
            max_rounds=max_rounds,
            require_citations=True,
            reasons=reasons,
        )
