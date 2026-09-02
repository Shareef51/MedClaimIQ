from __future__ import annotations

from app.domain.orchestration import AgentName, RoutingDecision, RoutingReason


class ClaimWorkflowRouter:
    """Deterministic supervisor/router.

    The router may later consume structured classifier outputs, but routing rules remain
    explicit and testable. It never changes tenant/claim scope or evidence-pack binding.
    """

    def route(
        self,
        *,
        source_types: tuple[str, ...],
        has_material_contradiction: bool,
        guardrail_decision: str | None,
        no_evidence: bool,
    ) -> RoutingDecision:
        selected: list[AgentName] = [AgentName.INTAKE, AgentName.POLICY, AgentName.ELIGIBILITY]
        reasons: list[RoutingReason] = [RoutingReason.DEFAULT_VERIFICATION]
        lowered = {item.lower() for item in source_types}
        if any("fhir" in item or "hospital" in item or "encounter" in item or "eob" in item for item in lowered):
            selected.append(AgentName.HOSPITAL_VERIFICATION)
            reasons.append(RoutingReason.HAS_HOSPITAL_EVIDENCE)
        if any("invoice" in item or "claim_line" in item or "bill" in item for item in lowered):
            selected.append(AgentName.INVOICE_VERIFICATION)
            reasons.append(RoutingReason.HAS_FINANCIAL_EVIDENCE)
        if any("coding" in item or "cpt" in item or "icd" in item for item in lowered):
            selected.append(AgentName.CODING)
            reasons.append(RoutingReason.HAS_CODING_EVIDENCE)
        selected.extend((AgentName.DUPLICATE_CLAIM, AgentName.FRAUD_WASTE, AgentName.DENIAL_RISK))
        if has_material_contradiction:
            reasons.append(RoutingReason.MATERIAL_CONTRADICTION)
        if guardrail_decision in {"block", "escalate"}:
            reasons.append(RoutingReason.GUARDRAIL_ESCALATION)
        if no_evidence:
            reasons.append(RoutingReason.NO_EVIDENCE)
        # Stable de-duplication is important for replay/checkpoint determinism.
        unique = tuple(dict.fromkeys(selected))
        parallel = tuple(agent for agent in unique if agent not in {AgentName.INTAKE})
        return RoutingDecision(
            selected_agents=unique,
            reasons=tuple(dict.fromkeys(reasons)),
            parallel_groups=((AgentName.INTAKE,), parallel, (AgentName.EVIDENCE_FUSION, AgentName.CRITIC)),
        )
