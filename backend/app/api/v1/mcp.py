from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.v1.rag import _authorize_claim_read, _identity
from app.core.mcp_factory import build_mcp_circuit_breakers, build_mcp_registry
from app.core.config import get_settings
from app.db.session import get_db
from app.domain.access import AccessRequest, Permission, ResourceAccessContext, ResourceType, ROLE_PERMISSIONS
from app.domain.mcp import MCPInvocationContext, MCPPolicyError
from app.mcp.gateway import MCPGateway
from app.schemas.mcp import (
    MCPApprovalDecisionRequest, MCPApprovalResponse, MCPHealthResponse, MCPInvokeRequest,
    MCPInvokeResponse, MCPToolDescription, MCPJSONRPCRequest, MCPInvocationTelemetryItem,
)
from app.services.authorization import authorization_service
from app.services.mcp import mcp_model_contract

router = APIRouter(tags=["mcp"])


@router.get("/mcp-model")
def model_contract() -> dict[str, object]:
    return mcp_model_contract()


def _claim_resource(claim) -> ResourceAccessContext:
    return ResourceAccessContext(
        resource_type=ResourceType.CLAIM, resource_id=claim.claim_id,
        owner_tenant_id=claim.tenant_id, owner_patient_subject_id=claim.patient_subject_id,
        related_provider_organization_id=claim.provider_organization_id,
        assigned_reviewer_user_id=claim.assigned_reviewer_user_id,
    )


def _authorize_permission(identity, claim, permission: Permission) -> None:
    decision = authorization_service.evaluate(AccessRequest(
        principal=identity.principal, permission=permission, resource=_claim_resource(claim),
    ))
    if not decision.allowed:
        raise HTTPException(status_code=403, detail=f"tool permission denied: {permission.value}")


@router.get("/mcp/tools", response_model=list[MCPToolDescription])
def list_tools(request: Request) -> list[MCPToolDescription]:
    identity = _identity(request)
    permissions = ROLE_PERMISSIONS[identity.principal.role]
    return [MCPToolDescription(
        name=tool.spec.name, version=tool.spec.version, description=tool.spec.description,
        risk_tier=tool.spec.risk_tier, required_permission=tool.spec.required_permission.value,
        allowed_agents=sorted(agent.value for agent in tool.spec.allowed_agents),
        supports_dry_run=tool.spec.supports_dry_run,
        requires_human_approval=tool.spec.requires_human_approval,
        external_side_effect=tool.spec.external_side_effect,
    ) for tool in build_mcp_registry().list() if tool.spec.required_permission in permissions]


@router.get("/mcp/health", response_model=MCPHealthResponse)
def health(request: Request) -> MCPHealthResponse:
    identity = _identity(request)
    if Permission.SYSTEM_HEALTH_READ not in ROLE_PERMISSIONS[identity.principal.role]:
        raise HTTPException(status_code=403, detail="system health permission is required")
    registry = build_mcp_registry()
    circuits = build_mcp_circuit_breakers()
    return MCPHealthResponse(
        status="ok", registry_tools=len(registry.list()),
        circuits={tool.spec.name: circuits.state(tool.spec.name).value for tool in registry.list()},
    )


@router.get("/claims/{claim_id}/mcp/telemetry", response_model=list[MCPInvocationTelemetryItem])
def claim_mcp_telemetry(
    claim_id: str, request: Request, limit: int = 100, db: Session = Depends(get_db),
) -> list[MCPInvocationTelemetryItem]:
    identity = _identity(request)
    claim = _authorize_claim_read(db, identity, claim_id)
    if Permission.CLAIM_REVIEW not in ROLE_PERMISSIONS[identity.principal.role] and Permission.AUDIT_READ not in ROLE_PERMISSIONS[identity.principal.role]:
        raise HTTPException(status_code=403, detail="claim review or audit permission is required")
    from app.repositories.mcp import MCPRepository
    rows = MCPRepository(db, identity.principal.tenant_id).list_invocations(claim.claim_id, limit=limit)
    return [MCPInvocationTelemetryItem(
        invocation_id=row.invocation_id, tool_name=row.tool_name, tool_version=row.tool_version,
        risk_tier=row.risk_tier, mode=row.mode, status=row.status, agent_name=row.agent_name,
        input_sha256=row.input_sha256, output_sha256=row.output_sha256, sanitized=row.sanitized,
        attempts=row.attempts, error_code=row.error_code, trace_id=row.trace_id,
        created_at=row.created_at, completed_at=row.completed_at,
    ) for row in rows]


@router.post("/claims/{claim_id}/mcp/tools/{tool_name}/invoke", response_model=MCPInvokeResponse)
def invoke_tool(
    claim_id: str, tool_name: str, payload: MCPInvokeRequest, request: Request,
    db: Session = Depends(get_db),
) -> MCPInvokeResponse:
    identity = _identity(request)
    claim = _authorize_claim_read(db, identity, claim_id)
    try:
        tool = build_mcp_registry().get(tool_name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="MCP tool was not found") from exc
    _authorize_permission(identity, claim, tool.spec.required_permission)
    if payload.agent_name and not payload.workflow_id:
        raise HTTPException(status_code=422, detail="agent_name requires workflow_id")
    idempotency_key = payload.idempotency_key or request.headers.get("Idempotency-Key")
    if not idempotency_key:
        raise HTTPException(status_code=400, detail="Idempotency-Key is required")
    context = MCPInvocationContext(
        tenant_id=identity.principal.tenant_id, claim_id=claim_id,
        actor_type="user", actor_id=identity.principal.user_id, actor_role=identity.principal.role.value,
        actor_permissions=ROLE_PERMISSIONS[identity.principal.role], workflow_id=payload.workflow_id,
        agent_name=payload.agent_name, trace_id=getattr(request.state, "trace_id", None) or request.headers.get("X-Trace-Id"),
    )
    gateway = MCPGateway(
        session=db, tenant_id=identity.principal.tenant_id, registry=build_mcp_registry(),
        circuit_breakers=build_mcp_circuit_breakers(), approval_ttl_minutes=get_settings().mcp_approval_ttl_minutes,
    )
    try:
        result = gateway.invoke(
            tool_name=tool_name, raw_input=payload.input, context=context, mode=payload.mode,
            idempotency_key=idempotency_key, approval_id=payload.approval_id,
        )
        db.commit()
    except MCPPolicyError as exc:
        db.rollback(); raise HTTPException(status_code=409, detail=str(exc)) from exc
    return MCPInvokeResponse(
        invocation_id=result.invocation_id, tool_name=result.tool_name, status=result.status,
        output=result.output, provenance=result.provenance, approval_id=result.approval_id,
        sanitized=result.sanitized, attempts=result.attempts,
    )


@router.post("/claims/{claim_id}/mcp/approvals/{approval_id}/decision", response_model=MCPApprovalResponse)
def decide_approval(
    claim_id: str, approval_id: str, payload: MCPApprovalDecisionRequest, request: Request,
    db: Session = Depends(get_db),
) -> MCPApprovalResponse:
    identity = _identity(request)
    claim = _authorize_claim_read(db, identity, claim_id)
    _authorize_permission(identity, claim, Permission.CLAIM_REVIEW)
    gateway = MCPGateway(
        session=db, tenant_id=identity.principal.tenant_id, registry=build_mcp_registry(),
        circuit_breakers=build_mcp_circuit_breakers(), approval_ttl_minutes=get_settings().mcp_approval_ttl_minutes,
    )
    try:
        approval = gateway.decide_approval(
            approval_id=approval_id, reviewer_user_id=identity.principal.user_id,
            decision=payload.decision, comment=payload.comment,
        )
        if approval.claim_id != claim_id:
            raise MCPPolicyError("approval is not bound to requested claim")
        db.commit()
    except MCPPolicyError as exc:
        db.rollback(); raise HTTPException(status_code=409, detail=str(exc)) from exc
    return MCPApprovalResponse(
        approval_id=approval.approval_id, status=approval.status,
        tool_name=approval.tool_name, claim_id=approval.claim_id,
    )

protocol_router = APIRouter(tags=["mcp-protocol"])
MCP_PROTOCOL_VERSION = get_settings().mcp_protocol_version


def _rpc_error(request_id, code: int, message: str):
    from app.schemas.mcp import MCPJSONRPCResponse
    return MCPJSONRPCResponse(id=request_id, error={"code": code, "message": message})


@protocol_router.post("/mcp")
def mcp_protocol(request_body: "MCPJSONRPCRequest", request: Request, db: Session = Depends(get_db)):
    from app.schemas.mcp import MCPJSONRPCResponse
    protocol_version = request.headers.get("MCP-Protocol-Version")
    method_header = request.headers.get("Mcp-Method")
    name_header = request.headers.get("Mcp-Name")
    if protocol_version != MCP_PROTOCOL_VERSION:
        return _rpc_error(request_body.id, -32600, "unsupported MCP protocol version")
    if method_header != request_body.method:
        return _rpc_error(request_body.id, -32600, "Mcp-Method header does not match JSON-RPC method")

    identity = _identity(request)
    if request_body.method == "server/discover":
        return MCPJSONRPCResponse(id=request_body.id, result={
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "capabilities": {"tools": {"listChanged": False}},
            "extensions": {},
        })

    if request_body.method == "tools/list":
        permissions = ROLE_PERMISSIONS[identity.principal.role]
        tools = []
        for tool in build_mcp_registry().list():
            if tool.spec.required_permission not in permissions:
                continue
            tools.append({
                "name": tool.spec.name,
                "description": tool.spec.description,
                "inputSchema": tool.input_schema.model_json_schema(),
                "outputSchema": tool.output_schema.model_json_schema(),
                "annotations": {
                    "readOnlyHint": tool.spec.risk_tier.value == "read_only",
                    "destructiveHint": False,
                    "idempotentHint": tool.spec.idempotent,
                    "openWorldHint": tool.spec.external_side_effect,
                },
            })
        return MCPJSONRPCResponse(id=request_body.id, result={
            "tools": tools, "ttlMs": 60000, "cacheScope": "private",
        })

    params = request_body.params
    tool_name = params.get("name")
    if not isinstance(tool_name, str) or not tool_name:
        return _rpc_error(request_body.id, -32602, "tools/call requires params.name")
    if name_header != tool_name:
        return _rpc_error(request_body.id, -32600, "Mcp-Name header does not match tools/call name")
    arguments = params.get("arguments", {})
    if not isinstance(arguments, dict):
        return _rpc_error(request_body.id, -32602, "tool arguments must be an object")
    claim_id = request.headers.get("X-MedClaimIQ-Claim-Id")
    if not claim_id:
        return _rpc_error(request_body.id, -32602, "X-MedClaimIQ-Claim-Id is required")
    claim = _authorize_claim_read(db, identity, claim_id)
    try:
        tool = build_mcp_registry().get(tool_name)
    except KeyError:
        return _rpc_error(request_body.id, -32602, "unknown tool")
    _authorize_permission(identity, claim, tool.spec.required_permission)

    meta = params.get("_meta", {}) if isinstance(params.get("_meta", {}), dict) else {}
    med_meta = meta.get("io.medclaimiq/tool", {}) if isinstance(meta.get("io.medclaimiq/tool", {}), dict) else {}
    try:
        from app.domain.mcp import MCPExecutionMode
        from app.domain.orchestration import AgentName
        mode = MCPExecutionMode(med_meta.get("mode", "read"))
        agent_name = AgentName(med_meta["agentName"]) if med_meta.get("agentName") else None
    except ValueError as exc:
        return _rpc_error(request_body.id, -32602, str(exc))
    workflow_id = med_meta.get("workflowId")
    if agent_name and not workflow_id:
        return _rpc_error(request_body.id, -32602, "agentName requires workflowId")
    idempotency_key = request.headers.get("Idempotency-Key") or med_meta.get("idempotencyKey")
    if not idempotency_key:
        return _rpc_error(request_body.id, -32602, "Idempotency-Key is required")
    context = MCPInvocationContext(
        tenant_id=identity.principal.tenant_id, claim_id=claim_id, actor_type="user",
        actor_id=identity.principal.user_id, actor_role=identity.principal.role.value,
        actor_permissions=ROLE_PERMISSIONS[identity.principal.role], workflow_id=workflow_id,
        agent_name=agent_name, trace_id=getattr(request.state, "trace_id", None) or request.headers.get("X-Trace-Id"),
    )
    gateway = MCPGateway(
        session=db, tenant_id=identity.principal.tenant_id, registry=build_mcp_registry(),
        circuit_breakers=build_mcp_circuit_breakers(), approval_ttl_minutes=get_settings().mcp_approval_ttl_minutes,
    )
    try:
        result = gateway.invoke(
            tool_name=tool_name, raw_input=arguments, context=context, mode=mode,
            idempotency_key=str(idempotency_key), approval_id=med_meta.get("approvalId"),
        )
        db.commit()
    except MCPPolicyError as exc:
        db.rollback()
        return _rpc_error(request_body.id, -32001, str(exc))
    structured = {
        "status": result.status.value, "invocationId": result.invocation_id,
        "output": result.output, "provenance": result.provenance,
        "approvalId": result.approval_id, "sanitized": result.sanitized,
    }
    return MCPJSONRPCResponse(id=request_body.id, result={
        "content": [{"type": "text", "text": "MedClaimIQ tool result available in structuredContent."}],
        "structuredContent": structured,
        "isError": result.status.value in {"failed", "denied"},
    })
