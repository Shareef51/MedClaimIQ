from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.claims import AuditEventModel, ClaimLineModel, ClaimModel, PolicyModel
from app.models.fhir import FHIRResourceSnapshotModel
from app.schemas.mcp import (
    AuditContextInput, AuditContextOutput, ClaimSummaryInput, ClaimSummaryOutput,
    FHIRResourceReadInput, FHIRResourceReadOutput, NotificationInput, NotificationOutput,
    PolicyLookupInput, PolicyLookupOutput, RequestEvidenceInput, RequestEvidenceOutput,
)


@dataclass(frozen=True, slots=True)
class MCPToolRuntime:
    session: Session
    tenant_id: str
    claim_id: str
    actor_type: str
    actor_id: str
    mode: str
    idempotency_key: str
    trace_id: str | None


def claim_summary(payload: ClaimSummaryInput, runtime: MCPToolRuntime) -> ClaimSummaryOutput:
    claim = runtime.session.scalar(select(ClaimModel).where(
        ClaimModel.tenant_id == runtime.tenant_id, ClaimModel.claim_id == runtime.claim_id,
    ))
    if claim is None:
        raise LookupError("claim was not found")
    lines: list[dict] = []
    if payload.include_lines:
        rows = runtime.session.scalars(select(ClaimLineModel).where(
            ClaimLineModel.tenant_id == runtime.tenant_id, ClaimLineModel.claim_id == runtime.claim_id,
        ).order_by(ClaimLineModel.line_number)).all()
        lines = [{
            "line_number": row.line_number, "code_system": row.code_system,
            "service_code": row.service_code, "service_date": row.service_date.isoformat(),
            "units": str(row.units), "amount": str(row.amount),
        } for row in rows]
    return ClaimSummaryOutput(
        claim_id=claim.claim_id, external_claim_ref=claim.external_claim_ref, status=claim.status,
        total_amount=str(claim.total_amount), currency=claim.currency,
        service_from=claim.service_from, service_to=claim.service_to, claim_lines=lines,
    )


def policy_lookup(payload: PolicyLookupInput, runtime: MCPToolRuntime) -> PolicyLookupOutput:
    claim = runtime.session.scalar(select(ClaimModel).where(
        ClaimModel.tenant_id == runtime.tenant_id, ClaimModel.claim_id == runtime.claim_id,
    ))
    if claim is None:
        raise LookupError("claim was not found")
    policy_id = payload.policy_id or claim.policy_id
    if policy_id is None:
        raise LookupError("claim has no bound policy")
    if payload.policy_id and payload.policy_id != claim.policy_id:
        raise PermissionError("tool cannot read a policy outside the bound claim")
    row = runtime.session.scalar(select(PolicyModel).where(
        PolicyModel.tenant_id == runtime.tenant_id, PolicyModel.policy_id == policy_id,
    ))
    if row is None:
        raise LookupError("policy was not found")
    return PolicyLookupOutput(
        policy_id=row.policy_id, policy_ref=row.policy_ref, plan_name=row.plan_name, status=row.status,
        effective_from=row.effective_from, effective_to=row.effective_to,
        policy_version=row.policy_version, source_system=row.source_system,
    )


def fhir_resource_read(payload: FHIRResourceReadInput, runtime: MCPToolRuntime) -> FHIRResourceReadOutput:
    stmt = select(FHIRResourceSnapshotModel).where(
        FHIRResourceSnapshotModel.tenant_id == runtime.tenant_id,
        FHIRResourceSnapshotModel.claim_id == runtime.claim_id,
        FHIRResourceSnapshotModel.resource_type == payload.resource_type,
    )
    if payload.logical_id:
        stmt = stmt.where(FHIRResourceSnapshotModel.logical_id == payload.logical_id)
    if payload.version_id:
        stmt = stmt.where(FHIRResourceSnapshotModel.version_id == payload.version_id)
    stmt = stmt.order_by(FHIRResourceSnapshotModel.fetched_at.desc()).limit(1)
    row = runtime.session.scalar(stmt)
    if row is None:
        raise LookupError("claim-scoped FHIR resource was not found")
    return FHIRResourceReadOutput(
        snapshot_id=row.snapshot_id, resource_type=row.resource_type, logical_id=row.logical_id,
        version_id=row.version_id, content_sha256=row.content_sha256,
        authoritative=row.authoritative, resource=row.canonical_resource or row.raw_resource,
    )


def audit_context(payload: AuditContextInput, runtime: MCPToolRuntime) -> AuditContextOutput:
    rows = runtime.session.scalars(select(AuditEventModel).where(
        AuditEventModel.tenant_id == runtime.tenant_id,
        AuditEventModel.resource_id == runtime.claim_id,
    ).order_by(AuditEventModel.occurred_at.desc()).limit(payload.limit)).all()
    return AuditContextOutput(events=[{
        "audit_event_id": row.audit_event_id, "actor_type": row.actor_type,
        "action": row.action, "resource_type": row.resource_type,
        "occurred_at": row.occurred_at.isoformat(), "details": row.details,
    } for row in rows])


def request_evidence(payload: RequestEvidenceInput, runtime: MCPToolRuntime) -> RequestEvidenceOutput:
    request_id = f"evidence_request_{sha256(runtime.idempotency_key.encode()).hexdigest()[:20]}"
    status = "preview" if runtime.mode == "dry_run" else "requested"
    if runtime.mode == "execute":
        existing = runtime.session.scalar(select(AuditEventModel).where(
            AuditEventModel.tenant_id == runtime.tenant_id,
            AuditEventModel.idempotency_key == f"mcp:{runtime.idempotency_key}",
        ))
        if existing is None:
            runtime.session.add(AuditEventModel(
                audit_event_id=f"audit_{uuid4().hex}", tenant_id=runtime.tenant_id,
                actor_type=runtime.actor_type, actor_id=runtime.actor_id,
                action="mcp.claim.request_evidence", resource_type="claim", resource_id=runtime.claim_id,
                trace_id=runtime.trace_id, idempotency_key=f"mcp:{runtime.idempotency_key}",
                details={"request_id": request_id, "evidence_types": payload.evidence_types,
                         "recipient_role": payload.recipient_role, "reason_sha256": sha256(payload.reason.encode()).hexdigest()},
                occurred_at=datetime.now(timezone.utc),
            ))
    return RequestEvidenceOutput(
        request_id=request_id, claim_id=runtime.claim_id, status=status,
        evidence_types=payload.evidence_types, recipient_role=payload.recipient_role,
    )


def notification_claim_update(payload: NotificationInput, runtime: MCPToolRuntime) -> NotificationOutput:
    # Synthetic/demo provider: no recipient address/body is persisted. Production adapters plug in behind this contract.
    notification_id = f"notification_{sha256(runtime.idempotency_key.encode()).hexdigest()[:20]}"
    recipient_hash = sha256(payload.recipient_ref.encode()).hexdigest()
    if runtime.mode == "dry_run":
        return NotificationOutput(
            notification_id=notification_id, status="preview", channel=payload.channel,
            recipient_ref_hash=recipient_hash,
        )
    provider_message_id = f"synthetic_{sha256((notification_id + payload.template_key).encode()).hexdigest()[:16]}"
    return NotificationOutput(
        notification_id=notification_id, status="sent_synthetic", channel=payload.channel,
        recipient_ref_hash=recipient_hash, provider_message_id=provider_message_id,
    )


def build_tool_handlers():
    return {
        "fhir.resource.read": fhir_resource_read,
        "policy.lookup": policy_lookup,
        "claims.summary.read": claim_summary,
        "audit.context.read": audit_context,
        "claim.request_evidence": request_evidence,
        "notification.claim_update": notification_claim_update,
    }
