from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from hashlib import sha256
from typing import Any


class WorkflowStatus(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    WAITING_HUMAN = "waiting_human"
    RETRY_PENDING = "retry_pending"
    FAILED = "failed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class AgentRunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    RETRY_PENDING = "retry_pending"
    FAILED = "failed"
    SKIPPED = "skipped"


class AgentName(StrEnum):
    INTAKE = "intake"
    HOSPITAL_VERIFICATION = "hospital_verification"
    INVOICE_VERIFICATION = "invoice_verification"
    ELIGIBILITY = "eligibility"
    POLICY = "policy"
    CODING = "coding"
    DUPLICATE_CLAIM = "duplicate_claim"
    FRAUD_WASTE = "fraud_waste"
    DENIAL_RISK = "denial_risk"
    EVIDENCE_FUSION = "evidence_fusion"
    CRITIC = "critic"
    DECISION_SUPPORT = "decision_support"
    HUMAN_REVIEW_ROUTER = "human_review_router"


class RoutingReason(StrEnum):
    DEFAULT_VERIFICATION = "default_verification"
    HAS_HOSPITAL_EVIDENCE = "has_hospital_evidence"
    HAS_FINANCIAL_EVIDENCE = "has_financial_evidence"
    HAS_CODING_EVIDENCE = "has_coding_evidence"
    MATERIAL_CONTRADICTION = "material_contradiction"
    GUARDRAIL_ESCALATION = "guardrail_escalation"
    NO_EVIDENCE = "no_evidence"


class HumanCheckpointReason(StrEnum):
    MATERIAL_CONTRADICTION = "material_contradiction"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    GUARDRAIL_BLOCK = "guardrail_block"
    AGENT_FAILURE = "agent_failure"
    FINAL_REVIEW_REQUIRED = "final_review_required"
    MULTIMODAL_CONFLICT = "multimodal_conflict"
    MISSING_REQUIRED_MODALITY = "missing_required_modality"


@dataclass(frozen=True, slots=True)
class EvidencePackBinding:
    pack_id: str
    claim_id: str
    content_sha256: str
    guardrail_run_id: str | None = None
    guardrail_decision: str | None = None


@dataclass(frozen=True, slots=True)
class AgentTask:
    agent: AgentName
    task_id: str
    depends_on: tuple[AgentName, ...] = ()
    max_attempts: int = 3
    timeout_seconds: int = 90
    required: bool = True


@dataclass(frozen=True, slots=True)
class AgentFinding:
    agent: AgentName
    finding_id: str
    summary: str
    confidence: float
    evidence_keys: tuple[str, ...] = ()
    risk_flags: tuple[str, ...] = ()
    requires_human_review: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def summary_sha256(self) -> str:
        return sha256(self.summary.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class AgentExecutionResult:
    agent: AgentName
    status: AgentRunStatus
    attempt: int
    findings: tuple[AgentFinding, ...] = ()
    error_code: str | None = None
    error_message: str | None = None
    retryable: bool = False


@dataclass(frozen=True, slots=True)
class HumanCheckpoint:
    checkpoint_id: str
    reason: HumanCheckpointReason
    message: str
    required_permissions: tuple[str, ...]
    evidence_pack_id: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class WorkflowState:
    workflow_id: str
    tenant_id: str
    claim_id: str
    thread_id: str
    status: WorkflowStatus
    evidence_pack: EvidencePackBinding
    selected_agents: tuple[AgentName, ...] = ()
    completed_agents: tuple[AgentName, ...] = ()
    failed_agents: tuple[AgentName, ...] = ()
    findings: tuple[AgentFinding, ...] = ()
    human_checkpoint: HumanCheckpoint | None = None
    retry_count: int = 0
    state_version: int = 1
    trace_id: str | None = None
    multimodal_context: Any | None = None


@dataclass(frozen=True, slots=True)
class RoutingDecision:
    selected_agents: tuple[AgentName, ...]
    reasons: tuple[RoutingReason, ...]
    parallel_groups: tuple[tuple[AgentName, ...], ...]


@dataclass(frozen=True, slots=True)
class ResumeCommand:
    checkpoint_id: str
    reviewer_user_id: str
    action: str
    comment: str | None = None


FINAL_DECISION_PROHIBITED_AGENTS = frozenset(AgentName)
