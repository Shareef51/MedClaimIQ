from __future__ import annotations

from dataclasses import replace

from app.domain.orchestration import (
    AgentExecutionResult, AgentRunStatus, HumanCheckpoint, WorkflowState, WorkflowStatus,
)


def apply_agent_result(state: WorkflowState, result: AgentExecutionResult) -> WorkflowState:
    completed = list(state.completed_agents)
    failed = list(state.failed_agents)
    if result.status == AgentRunStatus.SUCCEEDED and result.agent not in completed:
        completed.append(result.agent)
    if result.status == AgentRunStatus.FAILED and result.agent not in failed:
        failed.append(result.agent)
    return replace(
        state,
        completed_agents=tuple(completed),
        failed_agents=tuple(failed),
        findings=state.findings + result.findings,
        state_version=state.state_version + 1,
    )


def pause_for_human(state: WorkflowState, checkpoint: HumanCheckpoint) -> WorkflowState:
    return replace(
        state,
        status=WorkflowStatus.WAITING_HUMAN,
        human_checkpoint=checkpoint,
        state_version=state.state_version + 1,
    )


def resume_from_human(state: WorkflowState, *, checkpoint_id: str) -> WorkflowState:
    if state.status != WorkflowStatus.WAITING_HUMAN or state.human_checkpoint is None:
        raise ValueError("workflow is not waiting for human review")
    if state.human_checkpoint.checkpoint_id != checkpoint_id:
        raise ValueError("checkpoint does not match current workflow interrupt")
    return replace(
        state,
        status=WorkflowStatus.RUNNING,
        human_checkpoint=None,
        state_version=state.state_version + 1,
    )
