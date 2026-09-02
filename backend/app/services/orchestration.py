from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.access import Permission, ROLE_PERMISSIONS, UserRole
from app.domain.orchestration import AgentExecutionResult, HumanCheckpointReason, WorkflowStatus
from app.models.cross_source_rag import EvidencePackItemModel, EvidencePackModel
from app.models.grounding import RAGGuardrailRunModel
from app.models.orchestration import AgentExecutionModel, AgentFindingModel, AgentHumanCheckpointModel, AgentWorkflowEventModel, AgentWorkflowModel
from app.orchestration.router import ClaimWorkflowRouter
from app.repositories.orchestration import OrchestrationRepository
from app.schemas.orchestration import WorkflowResumeRequest, WorkflowStartRequest


class OrchestrationInvariantError(ValueError):
    pass


class OrchestrationService:
    def __init__(self, session: Session, tenant_id: str, *, router: ClaimWorkflowRouter | None = None) -> None:
        self.session = session
        self.tenant_id = tenant_id
        self.repo = OrchestrationRepository(session, tenant_id)
        self.router = router or ClaimWorkflowRouter()

    def start(self, *, claim_id: str, user_id: str, payload: WorkflowStartRequest, trace_id: str | None) -> AgentWorkflowModel:
        previous = self.repo.get_by_workflow_key(claim_id, payload.workflow_key)
        if previous is not None:
            if previous.evidence_pack_id != payload.evidence_pack_id:
                raise OrchestrationInvariantError("workflow key already bound to another evidence pack")
            return previous
        pack = self.session.scalar(select(EvidencePackModel).where(
            EvidencePackModel.tenant_id == self.tenant_id,
            EvidencePackModel.claim_id == claim_id,
            EvidencePackModel.pack_id == payload.evidence_pack_id,
        ))
        if pack is None:
            raise OrchestrationInvariantError("evidence pack is not available in the authorized claim scope")
        guardrail = None
        if payload.guardrail_run_id:
            guardrail = self.session.scalar(select(RAGGuardrailRunModel).where(
                RAGGuardrailRunModel.tenant_id == self.tenant_id,
                RAGGuardrailRunModel.claim_id == claim_id,
                RAGGuardrailRunModel.pack_id == pack.pack_id,
                RAGGuardrailRunModel.run_id == payload.guardrail_run_id,
            ))
            if guardrail is None:
                raise OrchestrationInvariantError("guardrail run is not bound to this evidence pack")
        source_types = tuple(self.session.scalars(select(EvidencePackItemModel.source_type).where(
            EvidencePackItemModel.tenant_id == self.tenant_id,
            EvidencePackItemModel.claim_id == claim_id,
            EvidencePackItemModel.pack_id == pack.pack_id,
        )))
        routing = self.router.route(
            source_types=source_types,
            has_material_contradiction=bool(pack.unresolved_material_contradictions),
            guardrail_decision=guardrail.decision if guardrail else None,
            no_evidence=bool(pack.no_evidence),
        )
        now = datetime.now(UTC)
        workflow_id = f"wf_{uuid4().hex}"
        model = self.repo.add_workflow(AgentWorkflowModel(
            workflow_id=workflow_id, tenant_id=self.tenant_id, claim_id=claim_id,
            evidence_pack_id=pack.pack_id, evidence_pack_sha256=self._pack_hash(pack),
            guardrail_run_id=guardrail.run_id if guardrail else None,
            workflow_key=payload.workflow_key, thread_id=f"lg_{uuid4().hex}",
            status=WorkflowStatus.CREATED.value, selected_agents=[a.value for a in routing.selected_agents],
            completed_agents=[], failed_agents=[], state_version=1, retry_count=0, trace_id=trace_id,
            created_by_user_id=user_id, created_at=now, updated_at=now,
        ))
        self._event(model, "workflow.created", "human", user_id, f"{payload.workflow_key}:created", trace_id, {
            "evidence_pack_id": pack.pack_id,
            "routing_reasons": [r.value for r in routing.reasons],
            "selected_agents": [a.value for a in routing.selected_agents],
        })
        if guardrail and guardrail.decision in {"block", "escalate"}:
            self.create_checkpoint(
                workflow=model, reason=HumanCheckpointReason.GUARDRAIL_BLOCK,
                message="Grounding guardrails require human review before agent workflow continues.",
                idempotency_key=f"{payload.workflow_key}:guardrail-checkpoint", trace_id=trace_id,
            )
        return model


    def mark_running(self, *, workflow_id: str, trace_id: str | None) -> AgentWorkflowModel:
        workflow = self.repo.get_workflow(workflow_id, for_update=True)
        if workflow is None:
            raise OrchestrationInvariantError("workflow does not exist in tenant scope")
        if workflow.status not in {WorkflowStatus.CREATED.value, WorkflowStatus.RETRY_PENDING.value, WorkflowStatus.RUNNING.value}:
            raise OrchestrationInvariantError(f"workflow cannot enter running from {workflow.status}")
        if workflow.status != WorkflowStatus.RUNNING.value:
            workflow.status = WorkflowStatus.RUNNING.value
            workflow.state_version += 1
            workflow.updated_at = datetime.now(UTC)
            self._event(
                workflow, "workflow.execution.started", "system", "langgraph-runner",
                f"execution-start:{workflow.workflow_id}", trace_id,
                {"thread_id": workflow.thread_id, "evidence_pack_id": workflow.evidence_pack_id},
            )
        return workflow

    def mark_completed(self, *, workflow_id: str, trace_id: str | None) -> AgentWorkflowModel:
        workflow = self.repo.get_workflow(workflow_id, for_update=True)
        if workflow is None:
            raise OrchestrationInvariantError("workflow does not exist in tenant scope")
        if workflow.status == WorkflowStatus.WAITING_HUMAN.value:
            raise OrchestrationInvariantError("human checkpoint must be resolved before workflow completion")
        if workflow.status != WorkflowStatus.COMPLETED.value:
            workflow.status = WorkflowStatus.COMPLETED.value
            workflow.state_version += 1
            workflow.updated_at = datetime.now(UTC)
            self._event(
                workflow, "workflow.execution.completed", "system", "langgraph-runner",
                f"execution-complete:{workflow.workflow_id}", trace_id,
                {"completed_agents": list(workflow.completed_agents), "failed_agents": list(workflow.failed_agents)},
            )
        return workflow

    def mark_failed(self, *, workflow_id: str, error_message: str, trace_id: str | None) -> AgentWorkflowModel:
        workflow = self.repo.get_workflow(workflow_id, for_update=True)
        if workflow is None:
            raise OrchestrationInvariantError("workflow does not exist in tenant scope")
        workflow.status = WorkflowStatus.FAILED.value
        workflow.state_version += 1
        workflow.updated_at = datetime.now(UTC)
        self._event(
            workflow, "workflow.execution.failed", "system", "langgraph-runner",
            f"execution-failed:{workflow.workflow_id}:{workflow.state_version}", trace_id,
            {"error_sha256": sha256(error_message.encode()).hexdigest()},
        )
        return workflow

    def record_agent_result(
        self, *, workflow_id: str, result: AgentExecutionResult, started_at: datetime,
        finished_at: datetime, trace_id: str | None,
    ) -> AgentExecutionModel:
        workflow = self.repo.get_workflow(workflow_id, for_update=True)
        if workflow is None:
            raise OrchestrationInvariantError("workflow does not exist in tenant scope")
        execution_id = f"aex_{uuid4().hex}"
        error_hash = sha256((result.error_message or "").encode()).hexdigest() if result.error_message else None
        execution = self.repo.add_execution(AgentExecutionModel(
            execution_id=execution_id, tenant_id=self.tenant_id, claim_id=workflow.claim_id,
            workflow_id=workflow.workflow_id, agent_name=result.agent.value, attempt=result.attempt,
            status=result.status.value, retryable=result.retryable, error_code=result.error_code,
            error_message_sha256=error_hash, started_at=started_at, finished_at=finished_at,
            latency_ms=max(0, int((finished_at - started_at).total_seconds() * 1000)),
            trace_id=trace_id, created_at=finished_at,
        ))
        for finding in result.findings:
            self.repo.add_finding(AgentFindingModel(
                finding_id=finding.finding_id, tenant_id=self.tenant_id, claim_id=workflow.claim_id,
                workflow_id=workflow.workflow_id, execution_id=execution.execution_id,
                agent_name=finding.agent.value, summary_sha256=finding.summary_sha256,
                confidence=finding.confidence, evidence_keys=list(finding.evidence_keys),
                risk_flags=list(finding.risk_flags), requires_human_review=finding.requires_human_review,
                finding_metadata=finding.metadata, created_at=finished_at,
            ))
        completed = set(workflow.completed_agents); failed = set(workflow.failed_agents)
        if result.status.value == "succeeded": completed.add(result.agent.value)
        if result.status.value == "failed": failed.add(result.agent.value)
        workflow.completed_agents = sorted(completed); workflow.failed_agents = sorted(failed)
        workflow.state_version += 1; workflow.updated_at = finished_at
        self._event(
            workflow, "agent.execution.completed", "agent", result.agent.value,
            f"execution:{workflow.workflow_id}:{result.agent.value}:{result.attempt}", trace_id,
            {"execution_id": execution.execution_id, "status": result.status.value,
             "attempt": result.attempt, "finding_count": len(result.findings),
             "retryable": result.retryable, "error_code": result.error_code},
        )
        return execution

    def create_checkpoint(self, *, workflow: AgentWorkflowModel, reason: HumanCheckpointReason, message: str, idempotency_key: str, trace_id: str | None, checkpoint_metadata: dict | None = None) -> AgentHumanCheckpointModel:
        if workflow.tenant_id != self.tenant_id:
            raise OrchestrationInvariantError("workflow tenant mismatch")
        now = datetime.now(UTC)
        checkpoint = self.repo.add_checkpoint(AgentHumanCheckpointModel(
            checkpoint_id=f"hcp_{uuid4().hex}", tenant_id=self.tenant_id, claim_id=workflow.claim_id,
            workflow_id=workflow.workflow_id, evidence_pack_id=workflow.evidence_pack_id,
            reason=reason.value, message_sha256=sha256(message.encode()).hexdigest(),
            required_permissions=[Permission.CLAIM_REVIEW.value], checkpoint_metadata=checkpoint_metadata or {}, status="waiting",
            created_at=now,
        ))
        workflow.status = WorkflowStatus.WAITING_HUMAN.value
        workflow.state_version += 1; workflow.updated_at = now
        self._event(workflow, "workflow.interrupted", "system", "langgraph", idempotency_key, trace_id, {"checkpoint_id": checkpoint.checkpoint_id, "reason": reason.value})
        return checkpoint

    def resume(self, *, workflow_id: str, reviewer_user_id: str, reviewer_role: UserRole, payload: WorkflowResumeRequest, trace_id: str | None) -> AgentWorkflowModel:
        if Permission.CLAIM_REVIEW not in ROLE_PERMISSIONS[reviewer_role]:
            raise OrchestrationInvariantError("reviewer lacks claim review permission")
        workflow = self.repo.get_workflow(workflow_id, for_update=True)
        checkpoint = self.repo.get_checkpoint(payload.checkpoint_id, for_update=True)
        if workflow is None or checkpoint is None or checkpoint.workflow_id != workflow_id:
            raise OrchestrationInvariantError("workflow checkpoint does not exist in tenant scope")
        if workflow.status != WorkflowStatus.WAITING_HUMAN.value or checkpoint.status != "waiting":
            raise OrchestrationInvariantError("workflow is not waiting at this checkpoint")
        now = datetime.now(UTC)
        checkpoint.status = "resumed" if payload.action == "continue" else ("cancelled" if payload.action == "cancel" else "evidence_requested")
        checkpoint.resumed_by_user_id = reviewer_user_id
        checkpoint.resume_action = payload.action
        checkpoint.resume_comment_sha256 = sha256((payload.comment or "").encode()).hexdigest() if payload.comment else None
        checkpoint.resumed_at = now
        if payload.action == "cancel":
            workflow.status = WorkflowStatus.CANCELLED.value
        elif payload.action == "request_more_evidence":
            # The evidence pack is immutable. Additional evidence requires a new pack/workflow;
            # this workflow remains human-paused rather than silently changing its evidence binding.
            workflow.status = WorkflowStatus.WAITING_HUMAN.value
        else:
            workflow.status = WorkflowStatus.RUNNING.value
        workflow.state_version += 1; workflow.updated_at = now
        event_type = "workflow.evidence_requested" if payload.action == "request_more_evidence" else "workflow.resumed"
        self._event(workflow, event_type, "human", reviewer_user_id, f"resume:{checkpoint.checkpoint_id}", trace_id, {"checkpoint_id": checkpoint.checkpoint_id, "action": payload.action})
        return workflow

    def _event(self, workflow, event_type, actor_type, actor_id, idempotency_key, trace_id, payload) -> None:
        self.repo.add_event(AgentWorkflowEventModel(
            event_id=f"awe_{uuid4().hex}", tenant_id=self.tenant_id, claim_id=workflow.claim_id,
            workflow_id=workflow.workflow_id, sequence=self.repo.next_event_sequence(workflow.workflow_id),
            event_type=event_type, actor_type=actor_type, actor_id=actor_id, idempotency_key=idempotency_key,
            event_payload=payload, trace_id=trace_id, occurred_at=datetime.now(UTC),
        ))

    @staticmethod
    def _pack_hash(pack: EvidencePackModel) -> str:
        material = f"{pack.pack_id}|{pack.query_sha256}|{pack.evidence_count}|{pack.contradiction_count}|{pack.planner_version}"
        return sha256(material.encode()).hexdigest()


def orchestration_model_contract() -> dict[str, object]:
    return {
        "framework": "LangGraph 1.x",
        "durability": {
            "thread_identity": "one stable thread_id per workflow",
            "checkpoint_store": "PostgreSQL LangGraph checkpointer",
            "strict_checkpoint_deserialization": True,
            "replay_safe_events": True,
        },
        "routing": {"supervisor": "deterministic", "parallel_fan_out": True, "fan_in": ["evidence_fusion", "critic"]},
        "execution_engine": {
            "graph_nodes": ["hydrate_evidence", "supervisor", "intake", "specialist", "evidence_fusion", "critic", "decision_support", "human_review_router", "human_gate"],
            "specialist_failure_isolation": True,
            "evidence_pack_rehydration_hash_check": True,
            "model_tool_audit_propagation": True,
            "execution_endpoint": "POST /claims/{claim_id}/agent-workflows/{workflow_id}/execute",
        },
        "streaming": {
            "transport": "SSE",
            "source": "append-only agent_workflow_events",
            "resume_cursor": "event sequence",
            "raw_evidence_in_stream": False,
        },
        "human_in_the_loop": {"interrupt_resume": True, "persisted_checkpoint_requests": True, "claim_review_permission_required": True},
        "safety_boundaries": [
            "agents cannot finalize claims",
            "agents receive evidence-pack bindings rather than unrestricted database access",
            "authorization and claim lifecycle transitions remain deterministic",
            "tenant, claim, and evidence-pack scope cannot be changed by agent output",
            "human review is required after guardrail escalation and before final claim decisions",
        ],
    }
