from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.claims import ClaimStatus, HumanDecision
from app.domain.governed_closure import DecisionPacketStatus, FINAL_FINANCIAL_DECISIONS, SecondReviewAction, ai_expected_human_decision
from app.models.claims import ClaimLineModel, ClaimModel, EvidenceArtifactModel
from app.models.evidence_graph import EvidenceContradictionModel
from app.models.governed_closure import AdjudicationAuditEventModel, DecisionNotificationIntentModel, DecisionSecondReviewModel, ReviewDecisionPacketModel
from app.models.grounding import RAGGuardrailRunModel
from app.models.multimodal_agent_orchestration import MultimodalAgentInvestigationModel
from app.models.multimodal_rag import MultimodalEvidencePackModel, MultimodalInconsistencyModel
from app.models.multimodal_review import MultimodalReviewAnnotationModel
from app.models.orchestration import AgentFindingModel, AgentHumanCheckpointModel
from app.repositories.governed_closure import GovernedClosureRepository
from app.repositories.tenancy import MembershipRepository
from app.schemas.claims import HumanDecisionCreate
from app.services.claims import ClaimDomainService
from app.services.review_workbench import ReviewConflictError, ReviewWorkbenchService


def _now() -> datetime:
    return datetime.now(UTC)


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _sha(value: object) -> str:
    raw=value if isinstance(value, str) else _canonical(value)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class GovernedClosureService:
    """Deterministic human-only decision governance.

    LLMs, agents, RAG and MCP may supply advisory evidence/finding references only.
    This service requires a live human reviewer lease and active reviewer membership
    for packet authorship/closure, and a distinct active reviewer for dual-control.
    """

    def __init__(self, session: Session, tenant_id: str):
        self.session=session; self.tenant_id=tenant_id
        self.repo=GovernedClosureRepository(session,tenant_id)
        self.review=ReviewWorkbenchService(session,tenant_id)

    def _claim(self, claim_id: str, *, for_update=False) -> ClaimModel:
        row=self.session.scalar((select(ClaimModel).where(ClaimModel.tenant_id==self.tenant_id,ClaimModel.claim_id==claim_id).with_for_update()) if for_update else select(ClaimModel).where(ClaimModel.tenant_id==self.tenant_id,ClaimModel.claim_id==claim_id))
        if row is None: raise LookupError("claim not found in tenant")
        return row

    def _require_reviewer(self, user_id: str) -> None:
        membership=MembershipRepository(self.session,self.tenant_id).get_by_user(user_id)
        if membership is None or membership.status!="active" or membership.role!="claims_reviewer":
            raise ReviewConflictError("active human claims reviewer membership required")

    def _snapshot(self, claim_id: str, evidence_ids: list[str]) -> list[dict[str, object]]:
        if not evidence_ids: raise ReviewConflictError("at least one evidence artifact is required")
        rows=[]
        for evidence_id in list(dict.fromkeys(evidence_ids)):
            row=self.session.scalar(select(EvidenceArtifactModel).where(EvidenceArtifactModel.tenant_id==self.tenant_id,EvidenceArtifactModel.claim_id==claim_id,EvidenceArtifactModel.evidence_id==evidence_id))
            if row is None: raise ReviewConflictError("decision evidence must belong to the reviewed claim")
            rows.append({"evidence_id":row.evidence_id,"content_sha256":row.content_sha256,"evidence_version":row.evidence_version,"status":row.status,"authoritative":row.authoritative,"document_type":row.document_type})
        return rows

    def _validate_refs(self, claim_id: str, finding_refs: list[str], annotation_refs: list[str], inconsistency_refs: list[str], checkpoint_refs: list[str]) -> None:
        checks=(
            (finding_refs,AgentFindingModel,AgentFindingModel.finding_id),
            (annotation_refs,MultimodalReviewAnnotationModel,MultimodalReviewAnnotationModel.annotation_id),
            (inconsistency_refs,MultimodalInconsistencyModel,MultimodalInconsistencyModel.inconsistency_id),
            (checkpoint_refs,AgentHumanCheckpointModel,AgentHumanCheckpointModel.checkpoint_id),
        )
        for ids,model,key in checks:
            if not ids: continue
            found=set(self.session.scalars(select(key).where(model.tenant_id==self.tenant_id,model.claim_id==claim_id,key.in_(set(ids)))))
            if found != set(ids): raise ReviewConflictError("packet contains a traceability reference outside the claim")

    def _validate_partial(self, claim: ClaimModel, decision: str, approved_amount: Decimal | None, partial_line_decisions: list[dict]) -> tuple[Decimal | None,Decimal | None]:
        total=Decimal(str(claim.total_amount or 0))
        if decision != HumanDecision.PARTIAL_APPROVE.value:
            if approved_amount is not None or partial_line_decisions: raise ReviewConflictError("partial approval amounts/lines are valid only for partial_approve")
            return None,None
        if approved_amount is None or approved_amount <= 0 or approved_amount >= total:
            raise ReviewConflictError("partial approval requires approved_amount greater than zero and lower than claim total")
        line_ids={x[0] for x in self.session.execute(select(ClaimLineModel.claim_line_id).where(ClaimLineModel.tenant_id==self.tenant_id,ClaimLineModel.claim_id==claim.claim_id)).all()}
        for item in partial_line_decisions:
            if item["claim_line_id"] not in line_ids: raise ReviewConflictError("partial approval references a claim line outside this claim")
        return approved_amount,total-approved_amount

    def _packet_payload(self, packet: ReviewDecisionPacketModel) -> dict[str, object]:
        return {
            "packet_id":packet.packet_id,"claim_id":packet.claim_id,"packet_version":packet.packet_version,
            "decision":packet.decision,"rationale":packet.rationale,"reason_codes":packet.reason_codes,
            "approved_amount":str(packet.approved_amount) if packet.approved_amount is not None else None,
            "denied_amount":str(packet.denied_amount) if packet.denied_amount is not None else None,
            "partial_line_decisions":packet.partial_line_decisions,"evidence_snapshot":packet.evidence_snapshot,
            "evidence_snapshot_sha256":packet.evidence_snapshot_sha256,"finding_refs":packet.finding_refs,
            "annotation_refs":packet.annotation_refs,"inconsistency_refs":packet.inconsistency_refs,"checkpoint_refs":packet.checkpoint_refs,
            "ai_recommendation":packet.ai_recommendation,"ai_disagreement":packet.ai_disagreement,
            "ai_disagreement_reason":packet.ai_disagreement_reason,"escalation_queue":packet.escalation_queue,
            "dual_control_required":packet.dual_control_required,"expected_claim_status_version":packet.expected_claim_status_version,
        }

    def _audit(self, claim_id: str, packet_id: str | None, event_type: str, actor_id: str, payload: dict, *, idempotency_key: str, trace_id: str | None=None, actor_type: str="human") -> AdjudicationAuditEventModel:
        prior=self.session.scalar(select(AdjudicationAuditEventModel).where(AdjudicationAuditEventModel.tenant_id==self.tenant_id,AdjudicationAuditEventModel.idempotency_key==idempotency_key))
        if prior: return prior
        events=self.repo.audit_events(claim_id); previous=events[-1].event_sha256 if events else None; now=_now(); sequence=self.repo.next_audit_sequence(claim_id)
        material={"previous":previous,"sequence":sequence,"event_type":event_type,"actor_type":actor_type,"actor_id":actor_id,"packet_id":packet_id,"payload":payload,"occurred_at":now.isoformat()}
        return self.repo.add(AdjudicationAuditEventModel(
            audit_event_id=f"ada_{uuid4().hex}",tenant_id=self.tenant_id,claim_id=claim_id,packet_id=packet_id,
            sequence=sequence,event_type=event_type,actor_type=actor_type,actor_id=actor_id,payload=payload,
            previous_event_sha256=previous,event_sha256=_sha(material),idempotency_key=idempotency_key,trace_id=trace_id,occurred_at=now,
        ))

    def save_packet(self, claim_id: str, reviewer_user_id: str, lock_token: str, *, decision: HumanDecision, rationale: str, reason_codes: list[str], evidence_snapshot_ids: list[str], finding_refs: list[str], annotation_refs: list[str], inconsistency_refs: list[str], checkpoint_refs: list[str], approved_amount: Decimal | None, partial_line_decisions: list[dict], ai_disagreement_reason: str | None, escalation_queue: str | None, expected_claim_status_version: int, expected_packet_version: int | None, idempotency_key: str, trace_id: str | None=None) -> ReviewDecisionPacketModel:
        self._require_reviewer(reviewer_user_id); self.review.verify_lock(claim_id,reviewer_user_id,lock_token)
        prior=self.repo.by_idempotency(idempotency_key)
        if prior:
            if prior.claim_id!=claim_id: raise ReviewConflictError("idempotency key belongs to another claim")
            return prior
        claim=self._claim(claim_id,for_update=True)
        if claim.status != ClaimStatus.HUMAN_REVIEW.value: raise ReviewConflictError("governed decision packet requires claim status human_review")
        if claim.status_version != expected_claim_status_version: raise ReviewConflictError("claim status version conflict; refresh before editing decision packet")
        latest=self.repo.latest_packet(claim_id,for_update=True)
        if latest and latest.status in {DecisionPacketStatus.CLOSED.value,DecisionPacketStatus.ESCALATED.value}: raise ReviewConflictError("claim already has a closed governed decision packet")
        if latest and latest.locked_at is not None and latest.status not in {DecisionPacketStatus.REJECTED_SECOND_REVIEW.value}: raise ReviewConflictError("locked decision packet cannot be revised; complete or reject the current version first")
        if latest and expected_packet_version is not None and latest.packet_version != expected_packet_version: raise ReviewConflictError("decision packet version conflict; another reviewer update exists")
        if not latest and expected_packet_version is not None: raise ReviewConflictError("no prior decision packet exists for expected packet version")
        if latest and latest.primary_reviewer_user_id != reviewer_user_id: raise ReviewConflictError("only the primary reviewer may revise this decision packet")
        if len(rationale.strip())<10 or not reason_codes: raise ReviewConflictError("mandatory rationale and at least one reason code are required")
        self._validate_refs(claim_id,finding_refs,annotation_refs,inconsistency_refs,checkpoint_refs)
        approved,denied=self._validate_partial(claim,decision.value,approved_amount,partial_line_decisions)
        recommendation=self.review.latest_ai_recommendation(claim_id); expected_ai=ai_expected_human_decision(recommendation); disagreement=bool(expected_ai and expected_ai!=decision.value)
        if disagreement and (not ai_disagreement_reason or len(ai_disagreement_reason.strip())<10): raise ReviewConflictError("AI-vs-human disagreement requires a documented human reason")
        if decision is HumanDecision.ESCALATE and not escalation_queue: raise ReviewConflictError("escalation_queue is required for an escalation decision")
        evidence_snapshot=self._snapshot(claim_id,evidence_snapshot_ids)
        packet=ReviewDecisionPacketModel(
            packet_id=f"rdp_{uuid4().hex}",tenant_id=self.tenant_id,claim_id=claim_id,primary_reviewer_user_id=reviewer_user_id,
            second_reviewer_user_id=None,status=DecisionPacketStatus.DRAFT.value,decision=decision.value,rationale=rationale.strip(),reason_codes=list(dict.fromkeys(reason_codes)),
            approved_amount=approved,denied_amount=denied,partial_line_decisions=partial_line_decisions,evidence_snapshot=evidence_snapshot,evidence_snapshot_sha256=_sha(evidence_snapshot),
            finding_refs=list(dict.fromkeys(finding_refs)),annotation_refs=list(dict.fromkeys(annotation_refs)),inconsistency_refs=list(dict.fromkeys(inconsistency_refs)),checkpoint_refs=list(dict.fromkeys(checkpoint_refs)),
            ai_recommendation=recommendation,ai_disagreement=disagreement,ai_disagreement_reason=ai_disagreement_reason.strip() if ai_disagreement_reason else None,
            completeness={},blocker_codes=[],escalation_queue=escalation_queue,dual_control_required=False,packet_version=(latest.packet_version+1 if latest else 1),
            expected_claim_status_version=expected_claim_status_version,locked_payload_sha256=None,decision_id=None,idempotency_key=idempotency_key,trace_id=trace_id,created_at=_now(),updated_at=_now(),locked_at=None,closed_at=None,
        )
        if latest and latest.status in {DecisionPacketStatus.DRAFT.value,DecisionPacketStatus.REJECTED_SECOND_REVIEW.value}:
            latest.status="superseded"; latest.updated_at=_now()
        self.repo.add(packet)
        self._audit(claim_id,packet.packet_id,"adjudication.packet.created",reviewer_user_id,{"packet_version":packet.packet_version,"decision":packet.decision,"evidence_snapshot_sha256":packet.evidence_snapshot_sha256},idempotency_key=f"packet-created:{idempotency_key}",trace_id=trace_id)
        self.review._event(claim_id,reviewer_user_id,"review.decision_packet.created",f"decision-packet:{idempotency_key}",{"packet_id":packet.packet_id,"packet_version":packet.packet_version,"decision":packet.decision},trace_id=trace_id)
        return packet

    def validation(self, packet: ReviewDecisionPacketModel) -> dict[str, object]:
        blockers=[]; details={}; claim=self._claim(packet.claim_id)
        current=[]
        for snap in packet.evidence_snapshot:
            row=self.session.scalar(select(EvidenceArtifactModel).where(EvidenceArtifactModel.tenant_id==self.tenant_id,EvidenceArtifactModel.claim_id==packet.claim_id,EvidenceArtifactModel.evidence_id==snap["evidence_id"]))
            if row is None:
                blockers.append("evidence_missing"); continue
            current.append(row)
            if row.status not in {"ready","accepted","processed"}: blockers.append("evidence_not_ready")
            if row.content_sha256!=snap["content_sha256"] or row.evidence_version!=snap["evidence_version"]: blockers.append("evidence_changed")
        details["evidence"]={"snapshot_count":len(packet.evidence_snapshot),"current_count":len(current),"authoritative_count":sum(1 for x in current if x.authoritative)}
        graph_conflicts=list(self.session.scalars(select(EvidenceContradictionModel).where(EvidenceContradictionModel.tenant_id==self.tenant_id,EvidenceContradictionModel.claim_id==packet.claim_id,EvidenceContradictionModel.status=="open",EvidenceContradictionModel.severity.in_(["material","high","critical"]))))
        if graph_conflicts: blockers.append("material_graph_conflict")
        resolution_ids=set(self.session.scalars(select(MultimodalReviewAnnotationModel.target_id).where(MultimodalReviewAnnotationModel.tenant_id==self.tenant_id,MultimodalReviewAnnotationModel.claim_id==packet.claim_id,MultimodalReviewAnnotationModel.target_type=="inconsistency",MultimodalReviewAnnotationModel.annotation_kind=="resolution")))
        mm_conflicts=list(self.session.scalars(select(MultimodalInconsistencyModel).where(MultimodalInconsistencyModel.tenant_id==self.tenant_id,MultimodalInconsistencyModel.claim_id==packet.claim_id,MultimodalInconsistencyModel.human_review_required.is_(True),MultimodalInconsistencyModel.severity.in_(["material","high","critical"]))))
        unresolved_mm=[x for x in mm_conflicts if x.inconsistency_id not in resolution_ids]
        if unresolved_mm: blockers.append("material_multimodal_conflict")
        investigations=list(self.session.scalars(select(MultimodalAgentInvestigationModel).where(MultimodalAgentInvestigationModel.tenant_id==self.tenant_id,MultimodalAgentInvestigationModel.claim_id==packet.claim_id)))
        latest_pack=self.session.scalar(select(MultimodalEvidencePackModel).where(MultimodalEvidencePackModel.tenant_id==self.tenant_id,MultimodalEvidencePackModel.claim_id==packet.claim_id).order_by(MultimodalEvidencePackModel.created_at.desc()).limit(1))
        available=set(latest_pack.modalities or []) if latest_pack else set(); required=set(); gap_count=0
        for inv in investigations:
            required.update(inv.required_modalities or []); gap_count+=int(inv.blocking_gap_count or 0)
        missing=sorted(required-available)
        if missing or gap_count: blockers.append("required_modality_missing")
        guardrail=self.session.scalar(select(RAGGuardrailRunModel).where(RAGGuardrailRunModel.tenant_id==self.tenant_id,RAGGuardrailRunModel.claim_id==packet.claim_id).order_by(RAGGuardrailRunModel.created_at.desc()).limit(1))
        if guardrail and guardrail.unresolved_material_contradictions>0: blockers.append("guardrail_conflict")
        if packet.ai_disagreement and not packet.ai_disagreement_reason: blockers.append("ai_disagreement_reason_missing")
        if not packet.reason_codes: blockers.append("reason_code_missing")
        if len(packet.rationale.strip())<10: blockers.append("rationale_missing")
        if packet.decision==HumanDecision.PARTIAL_APPROVE.value and (packet.approved_amount is None or packet.denied_amount is None): blockers.append("partial_approval_invalid")
        waiting_checkpoints=list(self.session.scalars(select(AgentHumanCheckpointModel).where(AgentHumanCheckpointModel.tenant_id==self.tenant_id,AgentHumanCheckpointModel.claim_id==packet.claim_id,AgentHumanCheckpointModel.status=="waiting")))
        blockers=list(dict.fromkeys(blockers))
        details.update({
            "material_graph_conflicts":len(graph_conflicts),"unresolved_multimodal_conflicts":len(unresolved_mm),
            "required_modalities":sorted(required),"available_modalities":sorted(available),"missing_modalities":missing,"blocking_modality_gaps":gap_count,
            "waiting_checkpoints":len(waiting_checkpoints),"guardrail_material_conflicts":int(guardrail.unresolved_material_contradictions if guardrail else 0),
            "evidence_snapshot_sha256":packet.evidence_snapshot_sha256,
        })
        can_finalize=not blockers
        # Escalation / information requests are allowed precisely because blockers can remain;
        # no financial adjudication occurs for these outcomes.
        if packet.decision in {HumanDecision.ESCALATE.value,HumanDecision.REQUEST_INFORMATION.value}: can_finalize=True
        details["complete_for_financial_decision"]=not blockers
        details["can_finalize_packet"]=can_finalize
        return {"blockers":blockers,"details":details,"claim_status_version":claim.status_version}

    def validate_and_lock(self, claim_id: str, packet_id: str, reviewer_user_id: str, lock_token: str, *, expected_packet_version: int, idempotency_key: str, trace_id: str | None=None) -> ReviewDecisionPacketModel:
        self._require_reviewer(reviewer_user_id); self.review.verify_lock(claim_id,reviewer_user_id,lock_token)
        packet=self.repo.get_packet(packet_id,for_update=True)
        if packet is None or packet.claim_id!=claim_id: raise LookupError("decision packet not found")
        if packet.primary_reviewer_user_id!=reviewer_user_id: raise ReviewConflictError("only the primary reviewer may validate this packet")
        if packet.status!=DecisionPacketStatus.DRAFT.value: return packet if packet.locked_at else (_ for _ in ()).throw(ReviewConflictError("only a draft decision packet can be validated"))
        if packet.packet_version!=expected_packet_version: raise ReviewConflictError("decision packet version conflict")
        claim=self._claim(claim_id,for_update=True)
        if claim.status_version!=packet.expected_claim_status_version: raise ReviewConflictError("claim changed after decision packet was drafted")
        result=self.validation(packet); packet.completeness=result["details"]; packet.blocker_codes=result["blockers"]
        if not result["details"]["can_finalize_packet"]: raise ReviewConflictError("decision packet blocked: "+", ".join(result["blockers"]))
        high_value=Decimal(str(claim.total_amount or 0))>=Decimal("10000")
        packet.dual_control_required=bool(packet.decision in {HumanDecision.DENY.value,HumanDecision.PARTIAL_APPROVE.value} or high_value or packet.ai_disagreement or "fraud_waste_signal" in packet.reason_codes)
        packet.locked_payload_sha256=_sha(self._packet_payload(packet)); packet.locked_at=_now(); packet.updated_at=_now()
        packet.status=DecisionPacketStatus.PENDING_SECOND_REVIEW.value if packet.dual_control_required else DecisionPacketStatus.READY_TO_CLOSE.value
        self.session.flush()
        self._audit(claim_id,packet.packet_id,"adjudication.packet.validated",reviewer_user_id,{"packet_version":packet.packet_version,"status":packet.status,"blockers":packet.blocker_codes,"dual_control_required":packet.dual_control_required,"locked_payload_sha256":packet.locked_payload_sha256},idempotency_key=f"packet-validated:{idempotency_key}",trace_id=trace_id)
        self.review._event(claim_id,reviewer_user_id,"review.decision_packet.validated",f"decision-packet-validated:{idempotency_key}",{"packet_id":packet.packet_id,"status":packet.status,"dual_control_required":packet.dual_control_required},trace_id=trace_id)
        return packet

    def second_review(self, claim_id: str, packet_id: str, reviewer_user_id: str, *, action: SecondReviewAction, rationale: str, expected_packet_version: int, idempotency_key: str, trace_id: str | None=None) -> ReviewDecisionPacketModel:
        self._require_reviewer(reviewer_user_id); packet=self.repo.get_packet(packet_id,for_update=True)
        if packet is None or packet.claim_id!=claim_id: raise LookupError("decision packet not found")
        if packet.packet_version!=expected_packet_version: raise ReviewConflictError("decision packet version conflict")
        if packet.status!=DecisionPacketStatus.PENDING_SECOND_REVIEW.value: raise ReviewConflictError("packet is not waiting for second review")
        if packet.primary_reviewer_user_id==reviewer_user_id: raise ReviewConflictError("dual-control reviewer must be different from the primary reviewer")
        if packet.locked_payload_sha256!=_sha(self._packet_payload(packet)): raise ReviewConflictError("locked decision packet payload changed unexpectedly")
        row=DecisionSecondReviewModel(second_review_id=f"dsr_{uuid4().hex}",tenant_id=self.tenant_id,claim_id=claim_id,packet_id=packet.packet_id,reviewer_user_id=reviewer_user_id,action=action.value,rationale=rationale.strip(),packet_version=packet.packet_version,payload_sha256=packet.locked_payload_sha256,created_at=_now())
        self.repo.add(row); packet.second_reviewer_user_id=reviewer_user_id; packet.updated_at=_now()
        if action is SecondReviewAction.APPROVE: packet.status=DecisionPacketStatus.READY_TO_CLOSE.value
        elif action is SecondReviewAction.REQUEST_CHANGES: packet.status=DecisionPacketStatus.REJECTED_SECOND_REVIEW.value
        else: packet.status=DecisionPacketStatus.REJECTED_SECOND_REVIEW.value
        self.session.flush()
        self._audit(claim_id,packet.packet_id,"adjudication.second_review.recorded",reviewer_user_id,{"action":action.value,"packet_version":packet.packet_version,"rationale_sha256":_sha(rationale)},idempotency_key=f"second-review:{idempotency_key}",trace_id=trace_id)
        self.review._event(claim_id,reviewer_user_id,"review.decision_packet.second_reviewed",f"second-review-event:{idempotency_key}",{"packet_id":packet.packet_id,"action":action.value,"status":packet.status},trace_id=trace_id)
        return packet

    def _resolve_checkpoints(self, packet: ReviewDecisionPacketModel, reviewer_user_id: str) -> list[str]:
        rows=list(self.session.scalars(select(AgentHumanCheckpointModel).where(AgentHumanCheckpointModel.tenant_id==self.tenant_id,AgentHumanCheckpointModel.claim_id==packet.claim_id,AgentHumanCheckpointModel.status=="waiting")))
        resolved=[]
        for row in rows:
            row.status="resolved_by_human_decision"; row.resumed_by_user_id=reviewer_user_id; row.resume_action=f"human_decision:{packet.decision}"; row.resume_comment_sha256=_sha(packet.rationale); row.resumed_at=_now(); resolved.append(row.checkpoint_id)
        self.session.flush(); return resolved

    def _notification_intents(self, packet: ReviewDecisionPacketModel) -> list[str]:
        audiences=("patient","provider","payer_operations") if packet.decision!=HumanDecision.ESCALATE.value else ("payer_operations","second_level_review")
        ids=[]
        for audience in audiences:
            key=f"decision-notification:{packet.packet_id}:{audience}"
            existing=self.session.scalar(select(DecisionNotificationIntentModel).where(DecisionNotificationIntentModel.tenant_id==self.tenant_id,DecisionNotificationIntentModel.idempotency_key==key))
            if existing: ids.append(existing.notification_id); continue
            payload={"claim_id":packet.claim_id,"packet_id":packet.packet_id,"decision":packet.decision,"audience":audience,"financial_values_disclosed":False}
            row=self.repo.add(DecisionNotificationIntentModel(notification_id=f"dni_{uuid4().hex}",tenant_id=self.tenant_id,claim_id=packet.claim_id,packet_id=packet.packet_id,audience=audience,notification_type="claim_review_resolution",status="pending_delivery",payload_sha256=_sha(payload),idempotency_key=key,created_at=_now(),delivered_at=None)); ids.append(row.notification_id)
        return ids

    def close(self, claim_id: str, packet_id: str, reviewer_user_id: str, lock_token: str, *, expected_packet_version: int, expected_claim_status_version: int, idempotency_key: str, trace_id: str | None=None) -> ReviewDecisionPacketModel:
        self._require_reviewer(reviewer_user_id); self.review.verify_lock(claim_id,reviewer_user_id,lock_token)
        packet=self.repo.get_packet(packet_id,for_update=True)
        if packet is None or packet.claim_id!=claim_id: raise LookupError("decision packet not found")
        if packet.primary_reviewer_user_id!=reviewer_user_id: raise ReviewConflictError("only the primary human reviewer may execute governed closure")
        if packet.packet_version!=expected_packet_version: raise ReviewConflictError("decision packet version conflict")
        if packet.status in {DecisionPacketStatus.CLOSED.value,DecisionPacketStatus.ESCALATED.value}: return packet
        if packet.status!=DecisionPacketStatus.READY_TO_CLOSE.value: raise ReviewConflictError("decision packet is not ready to close")
        if packet.dual_control_required and not packet.second_reviewer_user_id: raise ReviewConflictError("dual-control approval is required before closure")
        if packet.locked_payload_sha256!=_sha(self._packet_payload(packet)): raise ReviewConflictError("locked decision packet payload changed unexpectedly")
        claim=self._claim(claim_id,for_update=True)
        if claim.status_version!=expected_claim_status_version or claim.status_version!=packet.expected_claim_status_version: raise ReviewConflictError("claim version changed; governed closure aborted")
        fresh=self.validation(packet)
        if packet.decision in FINAL_FINANCIAL_DECISIONS and fresh["blockers"]:
            raise ReviewConflictError("closure blocked by newly changed evidence/conflict state: "+", ".join(fresh["blockers"]))
        result=ClaimDomainService(self.session,self.tenant_id).record_human_decision(claim_id,HumanDecisionCreate(
            decision_id=f"decision_{uuid4().hex}",reviewer_user_id=reviewer_user_id,decision=HumanDecision(packet.decision),rationale=packet.rationale,
            evidence_snapshot=[{"evidence_id":x["evidence_id"],"content_sha256":x["content_sha256"],"evidence_version":x["evidence_version"]} for x in packet.evidence_snapshot],idempotency_key=f"governed:{idempotency_key}",trace_id=trace_id,
        ))
        packet.decision_id=result.decision_id; packet.closed_at=_now(); packet.updated_at=_now(); packet.status=DecisionPacketStatus.ESCALATED.value if packet.decision==HumanDecision.ESCALATE.value else DecisionPacketStatus.CLOSED.value
        resolved=self._resolve_checkpoints(packet,reviewer_user_id); notifications=self._notification_intents(packet); self.session.flush()
        post_decision_notice_id=None
        if packet.status==DecisionPacketStatus.CLOSED.value:
            # Release 36 bootstrap is deterministic: it creates an evidence-bound notice DRAFT and
            # immutable decision-history version. Human release is a separate authorized action.
            from app.services.post_decision import PostDecisionService
            notice=PostDecisionService(self.session,self.tenant_id).bootstrap_after_closure(packet,reviewer_user_id,trace_id=trace_id)
            post_decision_notice_id=None if notice is None else notice.notice_id
        provenance={"decision_id":result.decision_id,"decision":packet.decision,"packet_version":packet.packet_version,"evidence_snapshot_sha256":packet.evidence_snapshot_sha256,"locked_payload_sha256":packet.locked_payload_sha256,"primary_reviewer_user_id":packet.primary_reviewer_user_id,"second_reviewer_user_id":packet.second_reviewer_user_id,"ai_recommendation":packet.ai_recommendation,"ai_disagreement":packet.ai_disagreement,"finding_refs":packet.finding_refs,"annotation_refs":packet.annotation_refs,"inconsistency_refs":packet.inconsistency_refs,"resolved_checkpoints":resolved,"notification_intents":notifications,"post_decision_notice_draft_id":post_decision_notice_id,"financial_execution_performed":False}
        self._audit(claim_id,packet.packet_id,"adjudication.claim.closed",reviewer_user_id,provenance,idempotency_key=f"claim-closure:{idempotency_key}",trace_id=trace_id)
        self.review._event(claim_id,reviewer_user_id,"review.claim.governed_closure",f"governed-closure:{idempotency_key}",{"packet_id":packet.packet_id,"decision_id":result.decision_id,"decision":packet.decision,"status":packet.status,"resolved_checkpoints":resolved},trace_id=trace_id)
        self.review._event(claim_id,reviewer_user_id,"review.notifications.queued",f"governed-notifications:{idempotency_key}",{"packet_id":packet.packet_id,"notification_intents":notifications},trace_id=trace_id)
        return packet

    def packet_view(self, packet: ReviewDecisionPacketModel) -> dict[str, object]:
        return {**self._packet_payload(packet),"primary_reviewer_user_id":packet.primary_reviewer_user_id,"status":packet.status,"blocker_codes":packet.blocker_codes or [],"completeness":packet.completeness or {},"second_reviewer_user_id":packet.second_reviewer_user_id,"decision_id":packet.decision_id,"created_at":packet.created_at,"updated_at":packet.updated_at,"locked_at":packet.locked_at,"closed_at":packet.closed_at,"locked_payload_sha256":packet.locked_payload_sha256}

    def snapshot(self, claim_id: str) -> dict[str, object]:
        claim=self._claim(claim_id); packet=self.repo.latest_packet(claim_id); audits=self.repo.audit_events(claim_id); notifications=self.repo.notifications(claim_id)
        return {
            "claim":{"claim_id":claim.claim_id,"status":claim.status,"status_version":claim.status_version,"total_amount":str(claim.total_amount),"currency":claim.currency},
            "decision_packet":None if packet is None else self.packet_view(packet),
            "validation":None if packet is None else self.validation(packet),
            "second_reviews":[] if packet is None else [{"second_review_id":x.second_review_id,"reviewer_user_id":x.reviewer_user_id,"action":x.action,"rationale":x.rationale,"packet_version":x.packet_version,"payload_sha256":x.payload_sha256,"created_at":x.created_at} for x in self.repo.second_reviews(packet.packet_id)],
            "audit_chain":[{"audit_event_id":x.audit_event_id,"sequence":x.sequence,"event_type":x.event_type,"actor_type":x.actor_type,"actor_id":x.actor_id,"previous_event_sha256":x.previous_event_sha256,"event_sha256":x.event_sha256,"occurred_at":x.occurred_at} for x in audits],
            "notifications":[{"notification_id":x.notification_id,"audience":x.audience,"notification_type":x.notification_type,"status":x.status,"created_at":x.created_at} for x in notifications],
            "human_authority":{"final_claim_decision_requires_authenticated_reviewer":True,"llm_can_adjudicate":False,"langgraph_can_adjudicate":False,"rag_can_adjudicate":False,"mcp_can_adjudicate":False,"automated_financial_execution":False},
        }

    def traceability(self, claim_id: str, packet_id: str | None=None) -> dict[str, object]:
        packet=self.repo.get_packet(packet_id) if packet_id else self.repo.latest_packet(claim_id)
        if packet is None or packet.claim_id!=claim_id: raise LookupError("decision packet not found")
        findings=[]
        if packet.finding_refs:
            findings=list(self.session.scalars(select(AgentFindingModel).where(AgentFindingModel.tenant_id==self.tenant_id,AgentFindingModel.claim_id==claim_id,AgentFindingModel.finding_id.in_(packet.finding_refs))))
        annotations=[]
        if packet.annotation_refs:
            annotations=list(self.session.scalars(select(MultimodalReviewAnnotationModel).where(MultimodalReviewAnnotationModel.tenant_id==self.tenant_id,MultimodalReviewAnnotationModel.claim_id==claim_id,MultimodalReviewAnnotationModel.annotation_id.in_(packet.annotation_refs))))
        nodes=[]; edges=[]
        for e in packet.evidence_snapshot: nodes.append({"id":e["evidence_id"],"type":"evidence","sha256":e["content_sha256"],"version":e["evidence_version"]})
        for f in findings:
            nodes.append({"id":f.finding_id,"type":"agent_finding","agent_name":f.agent_name,"advisory_only":True})
            for key in f.evidence_keys or []: edges.append({"from":str(key),"to":f.finding_id,"relationship":"supports_finding"})
        for a in annotations:
            nodes.append({"id":a.annotation_id,"type":"human_annotation","reviewer_user_id":a.reviewer_user_id}); edges.append({"from":a.target_id,"to":a.annotation_id,"relationship":"annotated_by_human"})
        nodes.append({"id":packet.packet_id,"type":"human_decision_packet","decision":packet.decision,"status":packet.status})
        for ref in packet.finding_refs: edges.append({"from":ref,"to":packet.packet_id,"relationship":"considered_by_human_decision"})
        for ref in packet.annotation_refs: edges.append({"from":ref,"to":packet.packet_id,"relationship":"considered_by_human_decision"})
        for e in packet.evidence_snapshot: edges.append({"from":e["evidence_id"],"to":packet.packet_id,"relationship":"bound_to_decision_snapshot"})
        if packet.decision_id: nodes.append({"id":packet.decision_id,"type":"persisted_human_decision"}); edges.append({"from":packet.packet_id,"to":packet.decision_id,"relationship":"governed_closure"})
        return {"claim_id":claim_id,"packet_id":packet.packet_id,"nodes":nodes,"edges":edges,"evidence_to_finding_to_annotation_to_human_decision":True,"final_decision_human_only":True}
