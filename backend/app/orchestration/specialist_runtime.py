from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.agents.contracts import AgentContext, AgentRegistry
from app.agents.specialists import EvidenceBoundSpecialistAgent
from app.domain.orchestration import AgentExecutionResult, AgentFinding, AgentName, AgentRunStatus, EvidencePackBinding, WorkflowState, WorkflowStatus
from app.models.orchestration import AgentModelInvocationModel, AgentToolAuditModel
from app.models.llmops import AIUsageLedgerModel
from app.observability.tracing import current_span_id, current_trace_id, traced_operation
from app.observability.metrics import record_operation, record_tokens
from app.repositories.llmops import LLMOpsRepository
from app.services.llmops import estimate_model_cost
from app.core.config import get_settings
from app.repositories.orchestration import OrchestrationRepository
from app.services.orchestration import OrchestrationInvariantError, OrchestrationService


class SpecialistExecutionCoordinator:
    """Runs one registered specialist and persists both result and provider/tool audit."""

    def __init__(self, session: Session, tenant_id: str, registry: AgentRegistry) -> None:
        self.session = session
        self.tenant_id = tenant_id
        self.registry = registry
        self.repo = OrchestrationRepository(session, tenant_id)
        self.service = OrchestrationService(session, tenant_id)

    def run(
        self, *, workflow_id: str, agent_name: AgentName, attempt: int,
        trace_id: str | None = None, max_attempts: int | None = None,
        prior_findings: tuple[AgentFinding, ...] = (),
        multimodal_context=None,
    ):
        workflow = self.repo.get_workflow(workflow_id)
        if workflow is None:
            raise OrchestrationInvariantError("workflow does not exist in tenant scope")
        if agent_name.value not in workflow.selected_agents and agent_name not in {
            AgentName.EVIDENCE_FUSION, AgentName.CRITIC, AgentName.DECISION_SUPPORT, AgentName.HUMAN_REVIEW_ROUTER,
        }:
            raise OrchestrationInvariantError("agent is not selected for this workflow")
        state = WorkflowState(
            workflow_id=workflow.workflow_id, tenant_id=workflow.tenant_id, claim_id=workflow.claim_id,
            thread_id=workflow.thread_id, status=WorkflowStatus(workflow.status),
            evidence_pack=EvidencePackBinding(
                workflow.evidence_pack_id, workflow.claim_id, workflow.evidence_pack_sha256,
                workflow.guardrail_run_id, None,
            ),
            selected_agents=tuple(AgentName(item) for item in workflow.selected_agents),
            completed_agents=tuple(AgentName(item) for item in workflow.completed_agents),
            failed_agents=tuple(AgentName(item) for item in workflow.failed_agents),
            findings=prior_findings, trace_id=trace_id, multimodal_context=multimodal_context,
        )
        context = AgentContext(
            tenant_id=workflow.tenant_id, claim_id=workflow.claim_id, workflow_id=workflow.workflow_id,
            evidence_pack=state.evidence_pack, trace_id=trace_id,
        )
        agent = self.registry.get(agent_name)
        started = datetime.now(UTC)
        with traced_operation("langgraph.specialist.execute", attributes={"agent_name": agent_name.value, "workflow_id": workflow_id, "attempt": attempt}):
            result = agent.run(state=state, context=context, attempt=attempt)
        if (
            max_attempts is not None
            and result.status == AgentRunStatus.RETRY_PENDING
            and attempt >= max_attempts
        ):
            result = AgentExecutionResult(
                agent=result.agent, status=AgentRunStatus.FAILED, attempt=attempt, findings=result.findings,
                error_code="agent_retry_exhausted", error_message=result.error_message, retryable=False,
            )
        if result.status == AgentRunStatus.SUCCEEDED and multimodal_context is not None:
            from app.services.multimodal_agent_orchestration import deterministic_multimodal_review_finding
            forced = deterministic_multimodal_review_finding(agent_name, multimodal_context)
            if forced is not None:
                result = AgentExecutionResult(result.agent, result.status, result.attempt, result.findings + (forced,), result.error_code, result.error_message, result.retryable)
        finished = datetime.now(UTC)
        self.service.record_agent_result(
            workflow_id=workflow_id, result=result, started_at=started, finished_at=finished, trace_id=trace_id,
        )
        if isinstance(agent, EvidenceBoundSpecialistAgent) and agent.last_telemetry is not None:
            telemetry = agent.last_telemetry
            invocation_id = f"ami_{workflow.workflow_id}_{agent_name.value}_{attempt}"
            self.repo.add_model_invocation(AgentModelInvocationModel(
                invocation_id=invocation_id, tenant_id=self.tenant_id, claim_id=workflow.claim_id,
                workflow_id=workflow.workflow_id, agent_name=agent_name.value, attempt=attempt,
                evidence_pack_id=workflow.evidence_pack_id, model_name=telemetry.model,
                prompt_key=telemetry.prompt_key, prompt_version=telemetry.prompt_version,
                prompt_sha256=telemetry.prompt_sha256, input_context_sha256=telemetry.input_context_sha256,
                output_sha256=telemetry.output_sha256, provider_response_id=telemetry.response_id,
                input_tokens=telemetry.input_tokens, output_tokens=telemetry.output_tokens, created_at=finished,
            ))
            cost_usd, pricing_version = estimate_model_cost(get_settings(), telemetry.model, telemetry.input_tokens, telemetry.output_tokens)
            record_tokens(model=telemetry.model,input_tokens=telemetry.input_tokens,output_tokens=telemetry.output_tokens)
            record_operation(operation="llm.model",latency_ms=max(0,(finished-started).total_seconds()*1000),status=result.status.value,attributes={"model":telemetry.model,"agent":agent_name.value})
            LLMOpsRepository(self.session, self.tenant_id).add_usage(AIUsageLedgerModel(
                usage_id=f"aiu_{invocation_id}", tenant_id=self.tenant_id, claim_id=workflow.claim_id,
                workflow_id=workflow.workflow_id, trace_id=trace_id or current_trace_id(), span_id=current_span_id(),
                operation_kind="model", provider="openai", model_name=telemetry.model,
                prompt_key=telemetry.prompt_key, prompt_version=telemetry.prompt_version, prompt_sha256=telemetry.prompt_sha256,
                input_tokens=telemetry.input_tokens, output_tokens=telemetry.output_tokens, estimated_cost_usd=cost_usd,
                pricing_version=pricing_version, latency_ms=max(0, (finished-started).total_seconds()*1000), status=result.status.value,
                operation_metadata={"agent_name": agent_name.value, "attempt": attempt, "evidence_pack_id": workflow.evidence_pack_id, "multimodal_pack_id": getattr(multimodal_context, "pack_id", None)},
                occurred_at=finished, created_at=finished, updated_at=finished,
            ))
            for index, item in enumerate(telemetry.tool_audit, start=1):
                self.repo.add_tool_audit(AgentToolAuditModel(
                    audit_id=f"ata_{invocation_id}_{index}", tenant_id=self.tenant_id, claim_id=workflow.claim_id,
                    workflow_id=workflow.workflow_id, invocation_id=invocation_id, agent_name=agent_name.value,
                    tool_name=str(item["tool_name"]), input_sha256=str(item["input_sha256"]),
                    result_sha256=str(item["result_sha256"]), result_count=int(item["result_count"]), created_at=finished,
                ))
        return result
