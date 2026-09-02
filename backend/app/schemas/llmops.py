from __future__ import annotations
from pydantic import BaseModel, Field

class LLMOpsSummaryResponse(BaseModel):
    window_minutes:int; model_calls:int; input_tokens:int; output_tokens:int; estimated_cost_usd:float|None; unpriced_model_calls:int
    model_counts:dict[str,int]; model_latency_p95_ms:float; agent_executions:int; agent_error_rate:float; agent_latency_p95_ms:float; retrieval_runs:int; retrieval_latency_p95_ms:float
    retrieval_no_evidence_rate:float; mcp_invocations:int; mcp_error_rate:float; evaluation_runs:int; evaluation_block_rate:float; slo_events:list[dict]

class SLOEvaluateRequest(BaseModel): window_minutes:int=Field(default=60,ge=5,le=1440)
