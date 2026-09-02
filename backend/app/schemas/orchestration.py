from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class WorkflowStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evidence_pack_id: str = Field(min_length=3, max_length=128)
    workflow_key: str = Field(min_length=4, max_length=160)
    guardrail_run_id: str | None = None


class WorkflowResumeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    checkpoint_id: str = Field(min_length=3, max_length=128)
    action: str = Field(pattern="^(continue|request_more_evidence|cancel)$")
    comment: str | None = Field(default=None, max_length=2000)


class WorkflowResponse(BaseModel):
    workflow_id: str
    claim_id: str
    thread_id: str
    status: str
    evidence_pack_id: str
    selected_agents: list[str]
    completed_agents: list[str]
    failed_agents: list[str]
    state_version: int
    checkpoint_id: str | None = None


class WorkflowModelResponse(BaseModel):
    framework: str
    durability: dict[str, object]
    routing: dict[str, object]
    execution_engine: dict[str, object] = Field(default_factory=dict)
    streaming: dict[str, object] = Field(default_factory=dict)
    human_in_the_loop: dict[str, object]
    safety_boundaries: list[str]


class WorkflowExecuteResponse(BaseModel):
    workflow_id: str
    claim_id: str
    status: str
    checkpoint_id: str | None = None
    thread_id: str
    state_version: int


class WorkflowEventResponse(BaseModel):
    sequence: int
    event_type: str
    actor_type: str
    actor_id: str
    payload: dict[str, object]
    trace_id: str | None = None
    occurred_at: str
