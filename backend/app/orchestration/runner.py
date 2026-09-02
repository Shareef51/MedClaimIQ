from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.domain.orchestration import WorkflowStatus
from app.orchestration.checkpoint import LangGraphPostgresCheckpointerFactory
from app.orchestration.engine import EndToEndLangGraphBuilder, WorkflowExecutionNodes, initial_runtime_state
from app.orchestration.retry import RetryPolicy
from app.repositories.orchestration import OrchestrationRepository
from app.services.orchestration import OrchestrationInvariantError, OrchestrationService


@dataclass(frozen=True, slots=True)
class WorkflowRunResult:
    workflow_id: str
    status: str
    checkpoint_id: str | None
    last_state: dict[str, Any]


class LangGraphWorkflowRunner:
    """Run/resume the compiled durable graph around one persisted workflow."""

    def __init__(
        self,
        *,
        session_factory: sessionmaker,
        settings: Settings,
        registry_factory: Callable[[Session, str], object],
        multimodal_investigation_factory: Callable[[Session, str], object] | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.settings = settings
        self.registry_factory = registry_factory
        self.multimodal_investigation_factory = multimodal_investigation_factory
        self.retry_policy = RetryPolicy(
            max_attempts=settings.agent_workflow_default_max_attempts,
            base_delay_seconds=settings.agent_workflow_retry_base_seconds,
            max_delay_seconds=settings.agent_workflow_retry_max_seconds,
        )

    def execute(self, *, tenant_id: str, claim_id: str, workflow_id: str, trace_id: str | None = None) -> WorkflowRunResult:
        workflow = self._prepare(tenant_id=tenant_id, claim_id=claim_id, workflow_id=workflow_id, trace_id=trace_id)
        nodes = WorkflowExecutionNodes(
            session_factory=self.session_factory,
            registry_factory=self.registry_factory,
            retry_policy=self.retry_policy, multimodal_investigation_factory=self.multimodal_investigation_factory,
        )
        factory = LangGraphPostgresCheckpointerFactory(
            self.settings.database_url,
            strict_msgpack=self.settings.langgraph_strict_msgpack,
        )
        try:
            with factory.open() as checkpointer:
                graph = EndToEndLangGraphBuilder(nodes).build(checkpointer=checkpointer)
                config = {
                    "configurable": {"thread_id": workflow.thread_id},
                    "metadata": {"tenant_id": tenant_id, "claim_id": claim_id, "workflow_id": workflow_id},
                }
                last_state: dict[str, Any] = initial_runtime_state(
                    workflow_id=workflow_id, tenant_id=tenant_id, claim_id=claim_id, trace_id=trace_id
                )
                for update in graph.stream(last_state, config=config, stream_mode="updates"):
                    if isinstance(update, dict):
                        for node_update in update.values():
                            if isinstance(node_update, dict):
                                last_state.update(node_update)
            return self._finish_or_wait(tenant_id, workflow_id, last_state, trace_id)
        except Exception as exc:
            self._mark_failed(tenant_id, workflow_id, exc, trace_id)
            raise

    def resume_graph(
        self,
        *,
        tenant_id: str,
        claim_id: str,
        workflow_id: str,
        reviewer_payload: dict[str, Any],
        trace_id: str | None = None,
    ) -> WorkflowRunResult:
        with self.session_factory() as db:
            repo = OrchestrationRepository(db, tenant_id)
            workflow = repo.get_workflow(workflow_id)
            if workflow is None or workflow.claim_id != claim_id:
                raise OrchestrationInvariantError("workflow is not available in claim scope")
            thread_id = workflow.thread_id
        nodes = WorkflowExecutionNodes(
            session_factory=self.session_factory,
            registry_factory=self.registry_factory,
            retry_policy=self.retry_policy, multimodal_investigation_factory=self.multimodal_investigation_factory,
        )
        factory = LangGraphPostgresCheckpointerFactory(
            self.settings.database_url,
            strict_msgpack=self.settings.langgraph_strict_msgpack,
        )
        try:
            from langgraph.types import Command
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("langgraph is required to resume durable workflows") from exc
        with factory.open() as checkpointer:
            graph = EndToEndLangGraphBuilder(nodes).build(checkpointer=checkpointer)
            config = {
                "configurable": {"thread_id": thread_id},
                "metadata": {"tenant_id": tenant_id, "claim_id": claim_id, "workflow_id": workflow_id},
            }
            output = graph.invoke(Command(resume=reviewer_payload), config=config)
            last_state = dict(output or {})
        return self._finish_or_wait(tenant_id, workflow_id, last_state, trace_id)

    def _prepare(self, *, tenant_id: str, claim_id: str, workflow_id: str, trace_id: str | None):
        with self.session_factory() as db:
            service = OrchestrationService(db, tenant_id)
            repo = OrchestrationRepository(db, tenant_id)
            workflow = repo.get_workflow(workflow_id, for_update=True)
            if workflow is None or workflow.claim_id != claim_id:
                raise OrchestrationInvariantError("workflow is not available in claim scope")
            if workflow.status == WorkflowStatus.WAITING_HUMAN.value:
                raise OrchestrationInvariantError("workflow is waiting for human review")
            if workflow.status in {WorkflowStatus.CANCELLED.value, WorkflowStatus.COMPLETED.value}:
                raise OrchestrationInvariantError(f"workflow cannot execute from status {workflow.status}")
            service.mark_running(workflow_id=workflow_id, trace_id=trace_id)
            db.commit()
            return workflow

    def _finish_or_wait(self, tenant_id: str, workflow_id: str, last_state: dict[str, Any], trace_id: str | None) -> WorkflowRunResult:
        with self.session_factory() as db:
            repo = OrchestrationRepository(db, tenant_id)
            service = OrchestrationService(db, tenant_id)
            workflow = repo.get_workflow(workflow_id, for_update=True)
            if workflow is None:
                raise OrchestrationInvariantError("workflow disappeared during execution")
            checkpoint = repo.waiting_checkpoint(workflow_id)
            if checkpoint is None and workflow.status == WorkflowStatus.RUNNING.value:
                service.mark_completed(workflow_id=workflow_id, trace_id=trace_id)
            db.commit()
            return WorkflowRunResult(
                workflow_id=workflow_id,
                status=workflow.status,
                checkpoint_id=checkpoint.checkpoint_id if checkpoint else None,
                last_state=last_state,
            )

    def _mark_failed(self, tenant_id: str, workflow_id: str, exc: Exception, trace_id: str | None) -> None:
        with self.session_factory() as db:
            try:
                OrchestrationService(db, tenant_id).mark_failed(
                    workflow_id=workflow_id, error_message=str(exc), trace_id=trace_id
                )
                db.commit()
            except Exception:
                db.rollback()
