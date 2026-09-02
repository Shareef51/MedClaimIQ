from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.claims import ActorType, ClaimStatus, HumanDecision
from app.domain.orchestration import AgentName
from app.domain.realtime import EventEnvelope, EventTopic
from app.domain.review_workbench import ReviewPriorityInputs, ReviewWorkStatus, calculate_priority
from app.models.claims import AuditEventModel, ClaimModel, ClaimStatusEventModel, EvidenceArtifactModel, EvidenceLineageModel, HumanReviewDecisionModel
from app.models.cross_source_rag import EvidencePackContradictionModel, EvidencePackItemModel, EvidencePackModel
from app.models.evidence_graph import EvidenceContradictionModel, EvidenceGraphEdgeModel
from app.models.fhir import HospitalCrossVerificationModel
from app.models.grounding import RAGGuardrailRunModel, RAGHumanReviewEscalationModel
from app.models.mcp import MCPApprovalRequestModel
from app.models.orchestration import AgentFindingModel, AgentHumanCheckpointModel, AgentWorkflowModel
from app.models.review_workbench import ReviewActionEventModel, ReviewClaimLockModel, ReviewDecisionMetadataModel, ReviewerNoteModel, ReviewWorkItemModel
from app.models.portal import PortalDocumentRequestModel
from app.models.sla import SLAReviewQueueEntryModel, SLATimerModel
from app.realtime.events import enqueue_realtime_event
from app.repositories.claims import ClaimRepository, EvidenceRepository
from app.repositories.review_workbench import ReviewWorkbenchRepository
from app.repositories.tenancy import MembershipRepository
from app.schemas.claims import ClaimTransitionRequest, HumanDecisionCreate
from app.services.claims import ClaimDomainInvariantError, ClaimDomainService


class ReviewConflictError(RuntimeError):
    pass


class ReviewLockError(RuntimeError):
    pass


def _now() -> datetime:
    return datetime.now(UTC)


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class ReviewWorkbenchService:
    def __init__(self, session: Session, tenant_id: str):
        self.session = session
        self.tenant_id = tenant_id
        self.repo = ReviewWorkbenchRepository(session, tenant_id)
        self.claims = ClaimRepository(session, tenant_id)
        self.evidence = EvidenceRepository(session, tenant_id)

    def _claim(self, claim_id: str, *, for_update: bool = False) -> ClaimModel:
        row = self.claims.get_for_update(claim_id) if for_update else self.claims.get(claim_id)
        if row is None:
            raise LookupError("claim not found in tenant")
        return row

    def _priority_inputs(self, claim: ClaimModel, now: datetime) -> ReviewPriorityInputs:
        overdue = int(self.session.scalar(select(func.count()).select_from(SLATimerModel).where(
            SLATimerModel.tenant_id == self.tenant_id,
            SLATimerModel.claim_id == claim.claim_id,
            SLATimerModel.status.in_(["scheduled", "breached"]),
            SLATimerModel.due_at <= now,
        )) or 0)
        critical = int(self.session.scalar(select(func.count()).select_from(SLAReviewQueueEntryModel).where(
            SLAReviewQueueEntryModel.tenant_id == self.tenant_id,
            SLAReviewQueueEntryModel.claim_id == claim.claim_id,
            SLAReviewQueueEntryModel.status == "open",
            SLAReviewQueueEntryModel.priority == "critical",
        )) or 0)
        high = int(self.session.scalar(select(func.count()).select_from(SLAReviewQueueEntryModel).where(
            SLAReviewQueueEntryModel.tenant_id == self.tenant_id,
            SLAReviewQueueEntryModel.claim_id == claim.claim_id,
            SLAReviewQueueEntryModel.status == "open",
            SLAReviewQueueEntryModel.priority == "high",
        )) or 0)
        guardrails = int(self.session.scalar(select(func.count()).select_from(RAGHumanReviewEscalationModel).where(
            RAGHumanReviewEscalationModel.tenant_id == self.tenant_id,
            RAGHumanReviewEscalationModel.claim_id == claim.claim_id,
            RAGHumanReviewEscalationModel.status == "requested",
        )) or 0)
        checkpoints = int(self.session.scalar(select(func.count()).select_from(AgentHumanCheckpointModel).where(
            AgentHumanCheckpointModel.tenant_id == self.tenant_id,
            AgentHumanCheckpointModel.claim_id == claim.claim_id,
            AgentHumanCheckpointModel.status == "waiting",
        )) or 0)
        contradictions = int(self.session.scalar(select(func.count()).select_from(EvidenceContradictionModel).where(
            EvidenceContradictionModel.tenant_id == self.tenant_id,
            EvidenceContradictionModel.claim_id == claim.claim_id,
            EvidenceContradictionModel.status == "open",
            EvidenceContradictionModel.severity.in_(["material", "high", "critical"]),
        )) or 0)
        return ReviewPriorityInputs(
            claim_status=claim.status, overdue_timers=overdue, critical_sla_items=critical,
            high_sla_items=high, guardrail_escalations=guardrails,
            waiting_human_checkpoints=checkpoints, material_contradictions=contradictions,
            claim_amount=float(claim.total_amount or 0),
        )

    def refresh_work_item(self, claim_id: str, *, now: datetime | None = None) -> ReviewWorkItemModel:
        now = now or _now(); claim = self._claim(claim_id)
        score, band, reasons = calculate_priority(self._priority_inputs(claim, now))
        earliest_due = self.session.scalar(select(func.min(SLATimerModel.due_at)).where(
            SLATimerModel.tenant_id == self.tenant_id, SLATimerModel.claim_id == claim_id,
            SLATimerModel.status.in_(["scheduled", "breached"]),
        ))
        row = self.repo.get_work_item(claim_id, for_update=True)
        status = ReviewWorkStatus.RESOLVED.value if claim.status in {"completed", "appeal_ready", "cancelled"} else (
            ReviewWorkStatus.WAITING_EVIDENCE.value if claim.status == "pending_evidence" else
            ReviewWorkStatus.ASSIGNED.value if claim.assigned_reviewer_user_id else ReviewWorkStatus.OPEN.value
        )
        if row is None:
            row = self.repo.add(ReviewWorkItemModel(
                work_item_id=f"rwi_{uuid4().hex}", tenant_id=self.tenant_id, claim_id=claim_id,
                status=status, priority_score=score, priority_band=band.value,
                priority_reasons=reasons, assigned_reviewer_user_id=claim.assigned_reviewer_user_id,
                sla_due_at=earliest_due, source_updated_at=now,
            ))
        else:
            row.status=status; row.priority_score=score; row.priority_band=band.value
            row.priority_reasons=reasons; row.assigned_reviewer_user_id=claim.assigned_reviewer_user_id
            row.sla_due_at=earliest_due; row.source_updated_at=now
            self.session.flush()
        return row

    def refresh_queue(self, *, now: datetime | None = None) -> list[ReviewWorkItemModel]:
        now = now or _now()
        claims = list(self.session.scalars(select(ClaimModel).where(
            ClaimModel.tenant_id == self.tenant_id,
            ClaimModel.status.in_(["ai_reviewed", "human_review", "pending_evidence"]),
        )))
        for claim in claims:
            self.refresh_work_item(claim.claim_id, now=now)
        return self.repo.list_queue(limit=500)

    def acquire_lock(self, claim_id: str, reviewer_user_id: str, *, lease_seconds: int = 300, now: datetime | None = None) -> tuple[ReviewClaimLockModel, str]:
        now = now or _now(); claim = self._claim(claim_id, for_update=True)
        membership = MembershipRepository(self.session, self.tenant_id).get_by_user(reviewer_user_id)
        if membership is None or membership.status != "active" or membership.role != "claims_reviewer":
            raise ReviewLockError("active claims reviewer membership required")
        if claim.assigned_reviewer_user_id not in {None, reviewer_user_id}:
            raise ReviewConflictError("claim is assigned to another reviewer")
        row = self.repo.get_lock(claim_id, for_update=True)
        if row is not None and row.released_at is None and _as_utc(row.locked_until) > _as_utc(now) and row.reviewer_user_id != reviewer_user_id:
            raise ReviewConflictError("claim currently has an active review lock")
        token = secrets.token_urlsafe(32); token_hash = _sha(token); until = now + timedelta(seconds=lease_seconds)
        if row is None:
            row = self.repo.add(ReviewClaimLockModel(
                lock_id=f"rlock_{uuid4().hex}", tenant_id=self.tenant_id, claim_id=claim_id,
                reviewer_user_id=reviewer_user_id, lock_token_sha256=token_hash, lock_version=1,
                acquired_at=now, locked_until=until, released_at=None,
            ))
        else:
            row.reviewer_user_id=reviewer_user_id; row.lock_token_sha256=token_hash; row.lock_version += 1
            row.acquired_at=now; row.locked_until=until; row.released_at=None; self.session.flush()
        claim.assigned_reviewer_user_id = reviewer_user_id
        item = self.refresh_work_item(claim_id, now=now); item.status = ReviewWorkStatus.IN_REVIEW.value
        self._event(claim_id, reviewer_user_id, "review.lock.acquired", f"lock:{row.lock_id}:v{row.lock_version}", {"lock_version": row.lock_version, "locked_until": until.isoformat()})
        return row, token

    def verify_lock(self, claim_id: str, reviewer_user_id: str, token: str, *, now: datetime | None = None) -> ReviewClaimLockModel:
        now = now or _now(); row = self.repo.get_lock(claim_id, for_update=True)
        if row is None or row.released_at is not None or _as_utc(row.locked_until) <= _as_utc(now):
            raise ReviewLockError("active review lock required")
        if row.reviewer_user_id != reviewer_user_id or not secrets.compare_digest(row.lock_token_sha256, _sha(token)):
            raise ReviewLockError("review lock does not belong to this reviewer/session")
        return row

    def renew_lock(self, claim_id: str, reviewer_user_id: str, token: str, *, lease_seconds: int = 300) -> ReviewClaimLockModel:
        row = self.verify_lock(claim_id, reviewer_user_id, token); row.locked_until = _now() + timedelta(seconds=lease_seconds); self.session.flush()
        self._event(claim_id, reviewer_user_id, "review.lock.renewed", f"renew:{row.lock_id}:v{row.lock_version}:{int(row.locked_until.timestamp())}", {"locked_until": row.locked_until.isoformat()})
        return row

    def release_lock(self, claim_id: str, reviewer_user_id: str, token: str) -> None:
        row = self.verify_lock(claim_id, reviewer_user_id, token); row.released_at = _now(); self.session.flush()
        self._event(claim_id, reviewer_user_id, "review.lock.released", f"release:{row.lock_id}:v{row.lock_version}", {})

    def begin_review(self, claim_id: str, reviewer_user_id: str, token: str, *, idempotency_key: str, trace_id: str | None = None) -> ClaimModel:
        self.verify_lock(claim_id, reviewer_user_id, token); claim = self._claim(claim_id)
        if claim.status == ClaimStatus.AI_REVIEWED.value:
            ClaimDomainService(self.session, self.tenant_id).transition_claim(claim_id, ClaimTransitionRequest(
                status_event_id=f"status-{uuid4().hex}", to_status=ClaimStatus.HUMAN_REVIEW,
                actor_type=ActorType.HUMAN, actor_id=reviewer_user_id, reason="Reviewer began human review",
                idempotency_key=idempotency_key, trace_id=trace_id, expected_status_version=claim.status_version,
            ))
        elif claim.status != ClaimStatus.HUMAN_REVIEW.value:
            raise ReviewConflictError("claim is not ready for human review")
        item = self.refresh_work_item(claim_id); item.status = ReviewWorkStatus.IN_REVIEW.value
        self._event(claim_id, reviewer_user_id, "review.started", f"review:{idempotency_key}", {}, trace_id=trace_id)
        return self._claim(claim_id)

    def add_note(self, claim_id: str, reviewer_user_id: str, token: str, *, note_type: str, body: str, evidence_refs: list[str], idempotency_key: str, trace_id: str | None = None) -> ReviewerNoteModel:
        self.verify_lock(claim_id, reviewer_user_id, token)
        prior = self.repo.event_by_idempotency(f"note:{idempotency_key}")
        if prior:
            note_id = prior.payload.get("note_id")
            return self.session.get(ReviewerNoteModel, note_id)
        for evidence_id in evidence_refs:
            if self.evidence.get(evidence_id) is None:
                raise ReviewConflictError("note evidence reference is outside claim/tenant evidence")
        note = self.repo.add(ReviewerNoteModel(
            note_id=f"rnote_{uuid4().hex}", tenant_id=self.tenant_id, claim_id=claim_id,
            reviewer_user_id=reviewer_user_id, note_type=note_type, body=body, body_sha256=_sha(body),
            evidence_refs=evidence_refs, created_at=_now(),
        ))
        self._event(claim_id, reviewer_user_id, "review.note.added", f"note:{idempotency_key}", {"note_id":note.note_id,"note_type":note_type,"evidence_refs":evidence_refs}, trace_id=trace_id)
        return note

    def _snapshot(self, claim_id: str, evidence_ids: list[str]) -> list[dict[str, object]]:
        out=[]
        for evidence_id in evidence_ids:
            row=self.evidence.get(evidence_id)
            if row is None or row.claim_id != claim_id: raise ReviewConflictError("decision evidence must belong to claim")
            out.append({"evidence_id": row.evidence_id, "content_sha256": row.content_sha256, "evidence_version": row.evidence_version})
        return out

    def latest_ai_recommendation(self, claim_id: str) -> str | None:
        row = self.session.scalar(select(AgentFindingModel).where(
            AgentFindingModel.tenant_id==self.tenant_id, AgentFindingModel.claim_id==claim_id,
            AgentFindingModel.agent_name==AgentName.DECISION_SUPPORT.value,
        ).order_by(AgentFindingModel.created_at.desc()).limit(1))
        if row is None: return None
        return (row.finding_metadata or {}).get("recommendation")

    def request_more_evidence(self, claim_id: str, reviewer_user_id: str, token: str, *, rationale: str, requested_document_types: list[str], evidence_snapshot_ids: list[str], idempotency_key: str, trace_id: str | None = None):
        self.verify_lock(claim_id, reviewer_user_id, token)
        decision = ClaimDomainService(self.session, self.tenant_id).record_human_decision(claim_id, HumanDecisionCreate(
            decision_id=f"decision_{uuid4().hex}", reviewer_user_id=reviewer_user_id,
            decision=HumanDecision.REQUEST_INFORMATION, rationale=rationale,
            evidence_snapshot=self._snapshot(claim_id, evidence_snapshot_ids), idempotency_key=idempotency_key, trace_id=trace_id,
        ))
        item=self.refresh_work_item(claim_id); item.status=ReviewWorkStatus.WAITING_EVIDENCE.value
        portal_request=self.session.scalar(select(PortalDocumentRequestModel).where(PortalDocumentRequestModel.tenant_id==self.tenant_id,PortalDocumentRequestModel.source_decision_id==decision.decision_id))
        if portal_request is None:
            portal_request=PortalDocumentRequestModel(
                request_id=f"pdr_{uuid4().hex}",tenant_id=self.tenant_id,claim_id=claim_id,source_decision_id=decision.decision_id,
                requested_by_user_id=reviewer_user_id,requested_document_types=requested_document_types,instructions=rationale,
                status="open",due_at=None,created_at=_now(),updated_at=_now(),
            )
            self.session.add(portal_request); self.session.flush()
        self._event(claim_id, reviewer_user_id, "review.evidence.requested", f"evidence-request:{idempotency_key}", {"decision_id":decision.decision_id,"requested_document_types":requested_document_types}, trace_id=trace_id)
        self._event(claim_id, reviewer_user_id, "claim.missing_evidence.requested", f"missing-evidence-request:{idempotency_key}", {"request_id":portal_request.request_id,"decision_id":decision.decision_id}, trace_id=trace_id)
        return decision

    def record_decision(self, claim_id: str, reviewer_user_id: str, token: str, *, decision: HumanDecision, rationale: str, reason_codes: list[str], evidence_snapshot_ids: list[str], expected_claim_status_version: int, override_reason: str | None, idempotency_key: str, trace_id: str | None = None):
        self.verify_lock(claim_id, reviewer_user_id, token)
        claim=self._claim(claim_id, for_update=True)
        if claim.status_version != expected_claim_status_version: raise ReviewConflictError("claim status version conflict; refresh workbench")
        recommendation=self.latest_ai_recommendation(claim_id)
        map_ai={"support_approval":HumanDecision.APPROVE,"support_denial":HumanDecision.DENY,"pending_documents":HumanDecision.REQUEST_INFORMATION}
        override = recommendation in map_ai and map_ai[recommendation] != decision
        if override and (override_reason is None or len(override_reason.strip()) < 5):
            raise ReviewConflictError("override reason is required when human decision differs from AI recommendation")
        result=ClaimDomainService(self.session, self.tenant_id).record_human_decision(claim_id, HumanDecisionCreate(
            decision_id=f"decision_{uuid4().hex}", reviewer_user_id=reviewer_user_id,
            decision=decision, rationale=rationale, evidence_snapshot=self._snapshot(claim_id,evidence_snapshot_ids),
            idempotency_key=idempotency_key, trace_id=trace_id,
        ))
        existing=self.session.scalar(select(ReviewDecisionMetadataModel).where(ReviewDecisionMetadataModel.decision_id==result.decision_id))
        if existing is None:
            self.repo.add(ReviewDecisionMetadataModel(
                metadata_id=f"rdm_{uuid4().hex}", tenant_id=self.tenant_id, claim_id=claim_id, decision_id=result.decision_id,
                reason_codes=reason_codes, ai_recommendation=recommendation, override_ai_recommendation=override,
                override_reason=override_reason if override else None, expected_claim_status_version=expected_claim_status_version, created_at=_now(),
            ))
        item=self.refresh_work_item(claim_id); item.status=ReviewWorkStatus.RESOLVED.value if decision not in {HumanDecision.REQUEST_INFORMATION,HumanDecision.ESCALATE} else item.status
        self._event(claim_id, reviewer_user_id, "review.decision.recorded", f"decision:{idempotency_key}", {"decision_id":result.decision_id,"decision":decision.value,"reason_codes":reason_codes,"override_ai_recommendation":override}, trace_id=trace_id)
        return result

    def snapshot(self, claim_id: str) -> dict[str, object]:
        claim=self._claim(claim_id); now=_now(); self.refresh_work_item(claim_id, now=now)
        pack=self.session.scalar(select(EvidencePackModel).where(EvidencePackModel.tenant_id==self.tenant_id,EvidencePackModel.claim_id==claim_id).order_by(EvidencePackModel.created_at.desc()).limit(1))
        pack_items=[]; pack_contra=[]
        if pack:
            pack_items=list(self.session.scalars(select(EvidencePackItemModel).where(EvidencePackItemModel.tenant_id==self.tenant_id,EvidencePackItemModel.pack_id==pack.pack_id).order_by(EvidencePackItemModel.rank)))
            pack_contra=list(self.session.scalars(select(EvidencePackContradictionModel).where(EvidencePackContradictionModel.tenant_id==self.tenant_id,EvidencePackContradictionModel.pack_id==pack.pack_id)))
        workflow=self.session.scalar(select(AgentWorkflowModel).where(AgentWorkflowModel.tenant_id==self.tenant_id,AgentWorkflowModel.claim_id==claim_id).order_by(AgentWorkflowModel.created_at.desc()).limit(1))
        findings=list(self.session.scalars(select(AgentFindingModel).where(AgentFindingModel.tenant_id==self.tenant_id,AgentFindingModel.claim_id==claim_id).order_by(AgentFindingModel.created_at)))
        guardrail=self.session.scalar(select(RAGGuardrailRunModel).where(RAGGuardrailRunModel.tenant_id==self.tenant_id,RAGGuardrailRunModel.claim_id==claim_id).order_by(RAGGuardrailRunModel.created_at.desc()).limit(1))
        timers=list(self.session.scalars(select(SLATimerModel).where(SLATimerModel.tenant_id==self.tenant_id,SLATimerModel.claim_id==claim_id).order_by(SLATimerModel.due_at)))
        approvals=list(self.session.scalars(select(MCPApprovalRequestModel).where(MCPApprovalRequestModel.tenant_id==self.tenant_id,MCPApprovalRequestModel.claim_id==claim_id).order_by(MCPApprovalRequestModel.created_at.desc())))
        fhir=list(self.session.scalars(select(HospitalCrossVerificationModel).where(HospitalCrossVerificationModel.tenant_id==self.tenant_id,HospitalCrossVerificationModel.claim_id==claim_id).order_by(HospitalCrossVerificationModel.created_at.desc())))
        graph_edges=list(self.session.scalars(select(EvidenceGraphEdgeModel).where(EvidenceGraphEdgeModel.tenant_id==self.tenant_id,EvidenceGraphEdgeModel.claim_id==claim_id).limit(200)))
        contradictions=list(self.session.scalars(select(EvidenceContradictionModel).where(EvidenceContradictionModel.tenant_id==self.tenant_id,EvidenceContradictionModel.claim_id==claim_id).order_by(EvidenceContradictionModel.created_at.desc())))
        evidence=list(self.session.scalars(select(EvidenceArtifactModel).where(EvidenceArtifactModel.tenant_id==self.tenant_id,EvidenceArtifactModel.claim_id==claim_id).order_by(EvidenceArtifactModel.created_at)))
        lineage=list(self.session.scalars(select(EvidenceLineageModel).where(EvidenceLineageModel.tenant_id==self.tenant_id,EvidenceLineageModel.claim_id==claim_id)))
        notes=self.repo.notes(claim_id)
        timeline=[]
        for e in self.session.scalars(select(ClaimStatusEventModel).where(ClaimStatusEventModel.tenant_id==self.tenant_id,ClaimStatusEventModel.claim_id==claim_id)):
            timeline.append({"at":e.occurred_at,"type":"claim.status","summary":f"{e.from_status} -> {e.to_status}","actor_id":e.actor_id})
        for e in self.session.scalars(select(AuditEventModel).where(AuditEventModel.tenant_id==self.tenant_id,AuditEventModel.resource_type=="claim",AuditEventModel.resource_id==claim_id)):
            timeline.append({"at":e.occurred_at,"type":e.action,"summary":e.action,"actor_id":e.actor_id})
        for e in self.repo.events(claim_id):
            timeline.append({"at":e.occurred_at,"type":e.event_type,"summary":e.event_type,"actor_id":e.reviewer_user_id})
        timeline.sort(key=lambda x:x["at"])
        return {
            "server_time":now,
            "claim":{"claim_id":claim.claim_id,"status":claim.status,"status_version":claim.status_version,"assigned_reviewer_user_id":claim.assigned_reviewer_user_id,"total_amount":str(claim.total_amount),"currency":claim.currency,"service_from":claim.service_from,"service_to":claim.service_to},
            "evidence":[{"evidence_id":e.evidence_id,"document_type":e.document_type,"media_type":e.media_type,"status":e.status,"source_type":e.source_type,"source_locator":e.source_locator,"content_sha256":e.content_sha256,"evidence_version":e.evidence_version,"authoritative":e.authoritative} for e in evidence],
            "evidence_lineage":[{"parent_evidence_id":e.parent_evidence_id,"child_evidence_id":e.child_evidence_id,"relationship":e.relationship} for e in lineage],
            "evidence_pack": None if not pack else {"pack_id":pack.pack_id,"confidence":pack.confidence,"coverage":pack.coverage,"no_evidence":pack.no_evidence,"items":[{"evidence_key":i.evidence_key,"source_type":i.source_type,"source_id":i.source_id,"source_version":i.source_version,"citation":i.citation,"authority_rank":i.authority_rank,"confidence":i.confidence} for i in pack_items],"contradictions":[{"field_name":c.field_name,"severity":c.severity,"status":c.status} for c in pack_contra]},
            "fhir_verifications":[{"verification_id":v.verification_id,"status":v.status,"confidence":str(v.confidence),"findings":v.findings} for v in fhir],
            "graph":{"edges":[{"source":e.source_entity_id,"relationship":e.relationship_type,"target":e.target_entity_id,"confidence":str(e.confidence)} for e in graph_edges],"contradictions":[{"contradiction_id":c.contradiction_id,"field_name":c.field_name,"severity":c.severity,"status":c.status,"left_value":c.left_value,"right_value":c.right_value} for c in contradictions]},
            "agent_workflow":None if not workflow else {"workflow_id":workflow.workflow_id,"status":workflow.status,"selected_agents":workflow.selected_agents,"completed_agents":workflow.completed_agents,"failed_agents":workflow.failed_agents},
            "agent_findings":[{"agent_name":f.agent_name,"confidence":f.confidence,"evidence_keys":f.evidence_keys,"risk_flags":f.risk_flags,"requires_human_review":f.requires_human_review,"metadata":f.finding_metadata} for f in findings],
            "decision_support":{"recommendation":self.latest_ai_recommendation(claim_id)},
            "guardrail":None if not guardrail else {"run_id":guardrail.run_id,"decision":guardrail.decision,"answerable":guardrail.answerable,"evidence_quality":guardrail.evidence_quality,"unresolved_material_contradictions":guardrail.unresolved_material_contradictions,"escalation_reasons":guardrail.escalation_reasons},
            "mcp_approvals":[{"approval_id":a.approval_id,"tool_name":a.tool_name,"status":a.status,"expires_at":a.expires_at} for a in approvals],
            "sla":[{"timer_id":t.timer_id,"timer_type":t.timer_type,"status":t.status,"due_at":t.due_at,"seconds_remaining":int((t.due_at-now).total_seconds())} for t in timers],
            "review_notes":[{"note_id":n.note_id,"note_type":n.note_type,"body":n.body,"evidence_refs":n.evidence_refs,"reviewer_user_id":n.reviewer_user_id,"created_at":n.created_at} for n in notes],
            "timeline":timeline,
        }

    def _event(self, claim_id: str, reviewer_user_id: str, event_type: str, idempotency_key: str, payload: dict, *, trace_id: str | None = None):
        prior=self.repo.event_by_idempotency(idempotency_key)
        if prior: return prior
        now=_now(); row=self.repo.add(ReviewActionEventModel(
            event_id=f"revt_{uuid4().hex}", tenant_id=self.tenant_id, claim_id=claim_id,
            sequence=self.repo.next_sequence(claim_id), event_type=event_type, reviewer_user_id=reviewer_user_id,
            idempotency_key=idempotency_key, payload=payload, trace_id=trace_id, occurred_at=now,
        ))
        enqueue_realtime_event(self.session, envelope=EventEnvelope(
            event_id=row.event_id,event_type=event_type,tenant_id=self.tenant_id,claim_id=claim_id,
            aggregate_type="human_review",aggregate_id=claim_id,occurred_at=now,trace_id=trace_id,
            producer="medclaimiq-review-workbench",payload={"sequence":row.sequence,**payload},
        ),topic=EventTopic.CLAIMS.value)
        return row
