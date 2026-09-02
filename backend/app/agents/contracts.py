from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.domain.orchestration import AgentExecutionResult, AgentName, EvidencePackBinding, WorkflowState


@dataclass(frozen=True, slots=True)
class AgentContext:
    tenant_id: str
    claim_id: str
    workflow_id: str
    evidence_pack: EvidencePackBinding
    trace_id: str | None = None


class SpecialistAgent(ABC):
    """Reasoning-only agent contract.

    Agents receive a stable evidence-pack binding and may return findings. They do not
    receive database sessions, lifecycle mutators, authorization services, or a final
    claim-decision capability.
    """

    name: AgentName

    @abstractmethod
    def run(self, *, state: WorkflowState, context: AgentContext, attempt: int) -> AgentExecutionResult:
        raise NotImplementedError


class AgentRegistry:
    def __init__(self, agents: tuple[SpecialistAgent, ...] = ()) -> None:
        self._agents = {agent.name: agent for agent in agents}

    def register(self, agent: SpecialistAgent) -> None:
        if agent.name in self._agents:
            raise ValueError(f"agent already registered: {agent.name}")
        self._agents[agent.name] = agent

    def get(self, name: AgentName) -> SpecialistAgent:
        try:
            return self._agents[name]
        except KeyError as exc:
            raise KeyError(f"agent not registered: {name}") from exc

    def names(self) -> tuple[AgentName, ...]:
        return tuple(sorted(self._agents, key=lambda item: item.value))
