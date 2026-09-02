from __future__ import annotations
import hashlib, json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.domain.appeal_resolution import AppealDecisionPacketStatus, AppealFinalOutcome, AppealSecondReviewAction, MATERIAL_FINANCIAL_CHANGE_ABS, MATERIAL_FINANCIAL_CHANGE_PCT
from app.domain.appeal_reconsideration import AppealCheckpointStatus, AppealEvidenceSnapshotStatus
from app.domain.claims import HumanDecision
from app.domain.post_decision import AppealStatus, DecisionNoticeStatus, PostDecisionTaskType, REASON_CODE_EXPLANATIONS
from app.domain.realtime import EventEnvelope, EventTopic
from app.models.appeal_resolution import AppealDecisionPacketModel, AppealDecisionSecondReviewModel, AppealFinalResolutionModel, AppealResolutionAuditEventModel
from app.models.appeal_reconsideration import AppealRAGItemModel, AppealRAGRunModel, AppealReconsiderationCheckpointModel
from app.models.claims import ClaimModel
from app.models.governed_closure import ReviewDecisionPacketModel
from app.models.post_decision import AppealCaseModel, DecisionNoticeModel
from app.repositories.appeal_reconsideration import AppealReconsiderationRepository
from app.repositories.appeal_resolution import AppealResolutionRepository
from app.repositories.post_decision import PostDecisionRepository
from app.repositories.tenancy import MembershipRepository
from app.realtime.events import enqueue_realtime_event
from app.services.post_decision import PostDecisionService
from app.services.review_workbench import ReviewConflictError

FINAL={HumanDecision.APPROVE.value,HumanDecision.DENY.value,HumanDecision.PARTIAL_APPROVE.value}
def _now(): return datetime.now(UTC)
def _canonical(v): return json.dumps(v,sort_keys=True,separators=(",",":"),default=str)
def _sha(v): return hashlib.sha256((v if isinstance(v,str) else _canonical(v)).encode()).hexdigest()

class AppealResolutionService:
    """Human-only final appeal adjudication. No agent/RAG/MCP method can call close()."""
    def __init__(self,session:Session,tenant_id:str):
        self.session=session; self.tenant_id=tenant_id; self.repo=AppealResolutionRepository(session,tenant_id); self.reconsider=AppealReconsiderationRepository(session,tenant_id); self.post=PostDecisionRepository(session,tenant_id)
    def _require_reviewer(self,user_id:str):
        m=MembershipRepository(self.session,self.tenant_id).get_by_user(user_id)
        if m is None or m.status!="active" or m.role!="claims_reviewer": raise ReviewConflictError("active human claims reviewer membership required")
    def _appeal(self,claim_id,appeal_id,for_update=False):
        a=self.post.appeal(appeal_id,for_update=for_update)
        if a is None or a.claim_id!=claim_id: raise LookupError("appeal not found")
        return a
    def _original_packet(self,a:AppealCaseModel):
        p=self.session.scalar(select(ReviewDecisionPacketModel).where(ReviewDecisionPacketModel.tenant_id==self.tenant_id,ReviewDecisionPacketModel.packet_id==a.original_packet_id))
        if p is None or p.status!="closed" or not p.locked_payload_sha256: raise ReviewConflictError("immutable original human decision packet required")
        return p
    def _claim(self,claim_id):
        c=self.session.scalar(select(ClaimModel).where(ClaimModel.tenant_id==self.tenant_id,ClaimModel.claim_id==claim_id))
        if c is None: raise LookupError("claim not found")
        return c
    def _amount(self,p:ReviewDecisionPacketModel,c:ClaimModel)->Decimal:
        if p.decision==HumanDecision.APPROVE.value:return Decimal(str(c.total_amount))
        if p.decision==HumanDecision.DENY.value:return Decimal("0")
        if p.decision==HumanDecision.PARTIAL_APPROVE.value:return Decimal(str(p.approved_amount or 0))
        raise ReviewConflictError("original packet is not a final financial human decision")
    def _normalize_amount(self,decision:str,amount:Decimal,total:Decimal)->Decimal:
        amount=Decimal(str(amount)).quantize(Decimal("0.01")); total=Decimal(str(total)).quantize(Decimal("0.01"))
        if decision==HumanDecision.APPROVE.value:
            if amount!=total: raise ReviewConflictError("approve reconsideration amount must equal claim total")
        elif decision==HumanDecision.DENY.value:
            if amount!=Decimal("0.00"): raise ReviewConflictError("deny reconsideration amount must be zero")
        elif decision==HumanDecision.PARTIAL_APPROVE.value:
            if not (Decimal("0.00")<amount<total): raise ReviewConflictError("partial approval amount must be between zero and claim total")
        else: raise ReviewConflictError("final appeal resolution requires approve, deny, or partial_approve")
        return amount
    def _emit(self,claim_id,event_type,appeal_id,metadata,trace_id=None):
        return enqueue_realtime_event(self.session,envelope=EventEnvelope(event_id=f"apr_{uuid4().hex}",event_type=event_type,tenant_id=self.tenant_id,claim_id=claim_id,aggregate_type="appeal_resolution",aggregate_id=appeal_id,occurred_at=_now(),trace_id=trace_id,producer="medclaimiq-appeal-resolution",payload=metadata,metadata={k:v for k,v in metadata.items() if k in {"appeal_id","packet_id","status","resolution_id","notice_id","dual_control_required"}}),topic=EventTopic.CLAIMS.value)
    def _audit(self,claim_id,appeal_id,packet_id,event_type,actor_id,payload,idempotency_key,trace_id=None):
        prior=self.repo.audit(appeal_id); seq=self.repo.next_audit_sequence(appeal_id); prev=prior[-1].event_sha256 if prior else None; now=_now(); digest=_sha({"claim_id":claim_id,"appeal_id":appeal_id,"packet_id":packet_id,"sequence":seq,"event_type":event_type,"actor_id":actor_id,"payload":payload,"previous":prev,"occurred_at":now})
        return self.repo.add(AppealResolutionAuditEventModel(audit_event_id=f"apraud_{uuid4().hex}",tenant_id=self.tenant_id,claim_id=claim_id,appeal_id=appeal_id,packet_id=packet_id,sequence=seq,event_type=event_type,actor_type="human",actor_id=actor_id,payload=payload,previous_event_sha256=prev,event_sha256=digest,idempotency_key=idempotency_key,trace_id=trace_id,occurred_at=now))
    def _recommendation(self,appeal_id):
        rows=self.reconsider.recommendations(appeal_id); return rows[0] if rows else None
    def _validation(self,a:AppealCaseModel,packet:AppealDecisionPacketModel):
        snap=self.reconsider.latest_snapshot(a.appeal_id); blockers=[]; details={}
        if snap is None or snap.status!=AppealEvidenceSnapshotStatus.LOCKED.value or snap.snapshot_id!=packet.snapshot_id or snap.snapshot_sha256!=packet.snapshot_sha256: blockers.append("appeal_snapshot_not_locked_or_changed")
        comparisons=[] if snap is None else self.reconsider.comparisons(a.appeal_id,snap.snapshot_id); material=[x.comparison_id for x in comparisons if x.severity=="material"]
        unresolved=sorted(set(material)-set(packet.resolved_comparison_refs));
        if unresolved:blockers.append("unresolved_material_contradictions")
        open_missing=[x.request_id for x in self.reconsider.missing_requests(a.appeal_id) if x.status=="open"]
        if open_missing:blockers.append("open_missing_evidence_requests")
        if not packet.citation_refs:blockers.append("citations_required")
        if not packet.reason_codes:blockers.append("reason_codes_required")
        if len((packet.rationale or "").strip())<20:blockers.append("human_rationale_required")
        rag_item_ids=set(self.session.scalars(select(AppealRAGItemModel.item_id).join(AppealRAGRunModel,AppealRAGRunModel.run_id==AppealRAGItemModel.run_id).where(AppealRAGItemModel.tenant_id==self.tenant_id,AppealRAGItemModel.appeal_id==a.appeal_id,AppealRAGRunModel.snapshot_id==packet.snapshot_id)))
        comparison_ids={x.comparison_id for x in comparisons}; valid_refs=rag_item_ids|comparison_ids
        invalid=sorted(set(packet.citation_refs)-valid_refs)
        if invalid:blockers.append("invalid_citation_refs")
        annotation_ids={x.annotation_id for x in self.reconsider.annotations(a.appeal_id)}
        invalid_annotations=sorted(set(packet.annotation_refs)-annotation_ids)
        if invalid_annotations:blockers.append("invalid_annotation_refs")
        checkpoint_ids={x.checkpoint_id for x in self.reconsider.checkpoints(a.appeal_id)}
        invalid_checkpoints=sorted(set(packet.checkpoint_refs)-checkpoint_ids)
        if invalid_checkpoints:blockers.append("invalid_checkpoint_refs")
        if packet.recommendation_disagreement and not (packet.recommendation_disagreement_reason or "").strip(): blockers.append("recommendation_disagreement_reason_required")
        details={"snapshot_locked":snap is not None and snap.status=="locked","citation_count":len(packet.citation_refs),"invalid_citation_refs":invalid,"invalid_annotation_refs":invalid_annotations,"invalid_checkpoint_refs":invalid_checkpoints,"material_comparison_count":len(material),"unresolved_material_comparisons":unresolved,"open_missing_evidence_requests":open_missing,"reason_code_count":len(packet.reason_codes),"recommendation_disagreement":packet.recommendation_disagreement}
        return details,list(dict.fromkeys(blockers))
    def save_packet(self,claim_id,appeal_id,reviewer_user_id,*,outcome,controlling_decision,rationale,reason_codes,citation_refs,resolved_comparison_refs,annotation_refs,checkpoint_refs,reconsidered_approved_amount,recommendation_disagreement_reason,expected_appeal_version,expected_packet_version,idempotency_key,trace_id=None):
        self._require_reviewer(reviewer_user_id); existing=self.session.scalar(select(AppealDecisionPacketModel).where(AppealDecisionPacketModel.tenant_id==self.tenant_id,AppealDecisionPacketModel.idempotency_key==idempotency_key));
        if existing:return existing
        a=self._appeal(claim_id,appeal_id,True)
        if a.assigned_reviewer_user_id!=reviewer_user_id: raise ReviewConflictError("only the assigned independent human appeal reviewer may prepare the final packet")
        if a.appeal_version!=expected_appeal_version: raise ReviewConflictError("appeal version conflict")
        if a.status not in {AppealStatus.IN_REVIEW.value,AppealStatus.WAITING_SUPPLEMENTAL_EVIDENCE.value}: raise ReviewConflictError("appeal must be in independent human review")
        if self.repo.final_resolution(appeal_id): raise ReviewConflictError("appeal already has a final controlling resolution")
        if not reason_codes: raise ReviewConflictError("at least one human reason code is required")
        if len((rationale or "").strip())<20: raise ReviewConflictError("human appeal rationale must contain at least 20 characters")
        latest=self.repo.latest_packet(appeal_id)
        if latest is not None: raise ReviewConflictError("an appeal decision packet already exists; lock or close the existing version")
        original=self._original_packet(a); claim=self._claim(claim_id); snap=self.reconsider.latest_snapshot(appeal_id)
        if snap is None or snap.status!="locked": raise ReviewConflictError("locked appeal reconsideration evidence snapshot required")
        decision=controlling_decision.value if hasattr(controlling_decision,"value") else str(controlling_decision); out=outcome.value if hasattr(outcome,"value") else str(outcome)
        if decision not in FINAL: raise ReviewConflictError("controlling appeal outcome must be a final human financial decision")
        orig_amount=self._amount(original,claim); new_amount=self._normalize_amount(decision,Decimal(str(reconsidered_approved_amount)),Decimal(str(claim.total_amount)))
        if out==AppealFinalOutcome.AFFIRM.value and (decision!=original.decision or new_amount!=orig_amount): raise ReviewConflictError("affirm must preserve original decision and amount")
        if out==AppealFinalOutcome.OVERTURN.value and decision==original.decision: raise ReviewConflictError("overturn must change the original controlling decision")
        if out==AppealFinalOutcome.MODIFY.value and decision==original.decision and new_amount==orig_amount: raise ReviewConflictError("modify must change decision or approved amount")
        rec=self._recommendation(appeal_id); expected={"affirm":"affirm","consider_modify":"modify","consider_overturn":"overturn"}.get(None if rec is None else rec.recommendation)
        disagreement=bool(expected and expected!=out)
        if disagreement and not (recommendation_disagreement_reason or "").strip(): raise ReviewConflictError("human disagreement with recommendation requires rationale")
        delta=new_amount-orig_amount; pct=abs(delta)/max(abs(orig_amount),Decimal("1")); material=abs(delta)>=Decimal(str(MATERIAL_FINANCIAL_CHANGE_ABS)) or pct>=Decimal(str(MATERIAL_FINANCIAL_CHANGE_PCT)); dual=out=="overturn" or material
        now=_now(); row=self.repo.add(AppealDecisionPacketModel(packet_id=f"adp_{uuid4().hex}",tenant_id=self.tenant_id,claim_id=claim_id,appeal_id=appeal_id,primary_reviewer_user_id=reviewer_user_id,second_reviewer_user_id=None,snapshot_id=snap.snapshot_id,snapshot_sha256=snap.snapshot_sha256,recommendation_run_id=None if rec is None else rec.reconsideration_run_id,outcome=out,controlling_decision=decision,rationale=rationale.strip(),reason_codes=list(dict.fromkeys(reason_codes)),citation_refs=list(dict.fromkeys(citation_refs)),resolved_comparison_refs=list(dict.fromkeys(resolved_comparison_refs)),annotation_refs=list(dict.fromkeys(annotation_refs)),checkpoint_refs=list(dict.fromkeys(checkpoint_refs)),original_approved_amount=orig_amount,reconsidered_approved_amount=new_amount,financial_delta=delta,material_financial_change=material,recommendation_disagreement=disagreement,recommendation_disagreement_reason=recommendation_disagreement_reason,completeness={},blocker_codes=[],dual_control_required=dual,status="draft",packet_version=1,expected_appeal_version=expected_appeal_version,locked_payload_sha256=None,final_resolution_id=None,idempotency_key=idempotency_key,trace_id=trace_id,created_at=now,updated_at=now,locked_at=None,closed_at=None))
        comp,block=self._validation(a,row); row.completeness=comp; row.blocker_codes=block
        self._audit(claim_id,appeal_id,row.packet_id,"appeal_decision_packet_created",reviewer_user_id,{"packet_version":1,"outcome":out,"decision":decision,"dual_control_required":dual,"blockers":block},f"audit:{idempotency_key}",trace_id); self._emit(claim_id,"appeal.resolution.packet.created",appeal_id,{"appeal_id":appeal_id,"packet_id":row.packet_id,"status":row.status,"dual_control_required":dual},trace_id); return row
    def lock_packet(self,claim_id,appeal_id,packet_id,reviewer_user_id,*,expected_packet_version,idempotency_key,trace_id=None):
        self._require_reviewer(reviewer_user_id); p=self.repo.packet(packet_id,for_update=True); a=self._appeal(claim_id,appeal_id)
        if p is None or p.appeal_id!=appeal_id or p.claim_id!=claim_id: raise LookupError("appeal decision packet not found")
        if p.primary_reviewer_user_id!=reviewer_user_id: raise ReviewConflictError("only primary independent human reviewer may lock packet")
        if p.packet_version!=expected_packet_version: raise ReviewConflictError("appeal packet version conflict")
        if p.status not in {"draft","blocked"}: return p
        comp,block=self._validation(a,p); p.completeness=comp;p.blocker_codes=block
        if block: p.status="blocked";p.updated_at=_now(); raise ReviewConflictError("appeal decision packet blocked: "+",".join(block))
        payload={"appeal_id":appeal_id,"snapshot_sha256":p.snapshot_sha256,"outcome":p.outcome,"decision":p.controlling_decision,"rationale":p.rationale,"reason_codes":p.reason_codes,"citation_refs":p.citation_refs,"resolved_comparison_refs":p.resolved_comparison_refs,"original_amount":str(p.original_approved_amount),"new_amount":str(p.reconsidered_approved_amount),"financial_delta":str(p.financial_delta),"recommendation_disagreement":p.recommendation_disagreement,"primary_reviewer":p.primary_reviewer_user_id,"dual_control_required":p.dual_control_required}
        p.locked_payload_sha256=_sha(payload);p.locked_at=_now();p.status="pending_second_review" if p.dual_control_required else "locked";p.updated_at=_now()
        self._audit(claim_id,appeal_id,p.packet_id,"appeal_decision_packet_locked",reviewer_user_id,{"locked_payload_sha256":p.locked_payload_sha256,"dual_control_required":p.dual_control_required},f"audit:{idempotency_key}",trace_id);self._emit(claim_id,"appeal.resolution.packet.locked",appeal_id,{"appeal_id":appeal_id,"packet_id":p.packet_id,"status":p.status,"dual_control_required":p.dual_control_required},trace_id);return p
    def second_review(self,claim_id,appeal_id,packet_id,reviewer_user_id,*,action,rationale,expected_packet_version,idempotency_key,trace_id=None):
        self._require_reviewer(reviewer_user_id);p=self.repo.packet(packet_id,for_update=True);a=self._appeal(claim_id,appeal_id)
        if p is None or p.appeal_id!=appeal_id: raise LookupError("appeal decision packet not found")
        if not p.dual_control_required or p.status!="pending_second_review": raise ReviewConflictError("packet is not awaiting second-level human approval")
        if p.packet_version!=expected_packet_version: raise ReviewConflictError("appeal packet version conflict")
        original=self._original_packet(a); disallowed={p.primary_reviewer_user_id,original.primary_reviewer_user_id,original.second_reviewer_user_id}
        if reviewer_user_id in disallowed: raise ReviewConflictError("second-level appeal reviewer must be independent from primary and original adjudication reviewers")
        existing=self.session.scalar(select(AppealDecisionSecondReviewModel).where(AppealDecisionSecondReviewModel.tenant_id==self.tenant_id,AppealDecisionSecondReviewModel.packet_id==packet_id,AppealDecisionSecondReviewModel.reviewer_user_id==reviewer_user_id))
        if existing:return p
        act=action.value if hasattr(action,"value") else str(action);payload={"packet":packet_id,"locked":p.locked_payload_sha256,"reviewer":reviewer_user_id,"action":act,"rationale":rationale}
        self.repo.add(AppealDecisionSecondReviewModel(second_review_id=f"adsr_{uuid4().hex}",tenant_id=self.tenant_id,claim_id=claim_id,appeal_id=appeal_id,packet_id=packet_id,reviewer_user_id=reviewer_user_id,action=act,rationale=rationale,packet_version=p.packet_version,payload_sha256=_sha(payload),created_at=_now()))
        p.second_reviewer_user_id=reviewer_user_id;p.status="second_review_approved" if act=="approve" else "blocked";p.blocker_codes=[] if act=="approve" else list(dict.fromkeys([*p.blocker_codes,"second_review_rejected"]));p.updated_at=_now()
        self._audit(claim_id,appeal_id,p.packet_id,"appeal_second_review_recorded",reviewer_user_id,{"action":act,"locked_payload_sha256":p.locked_payload_sha256},f"audit:{idempotency_key}",trace_id);self._emit(claim_id,"appeal.resolution.second_review.completed",appeal_id,{"appeal_id":appeal_id,"packet_id":p.packet_id,"status":p.status},trace_id);return p
    def close(self,claim_id,appeal_id,packet_id,reviewer_user_id,*,expected_packet_version,expected_appeal_version,idempotency_key,trace_id=None):
        self._require_reviewer(reviewer_user_id);existing=self.session.scalar(select(AppealFinalResolutionModel).where(AppealFinalResolutionModel.tenant_id==self.tenant_id,AppealFinalResolutionModel.idempotency_key==idempotency_key));
        if existing:return existing
        p=self.repo.packet(packet_id,for_update=True);a=self._appeal(claim_id,appeal_id,True)
        if p is None or p.appeal_id!=appeal_id: raise LookupError("appeal decision packet not found")
        if p.primary_reviewer_user_id!=reviewer_user_id: raise ReviewConflictError("only primary independent human appeal reviewer may finalize the resolution")
        if p.packet_version!=expected_packet_version: raise ReviewConflictError("appeal packet version conflict")
        if a.appeal_version!=expected_appeal_version: raise ReviewConflictError("appeal version conflict")
        allowed={"locked","second_review_approved"};
        if p.status not in allowed: raise ReviewConflictError("appeal decision packet is not eligible for final human closure")
        if p.dual_control_required and p.status!="second_review_approved": raise ReviewConflictError("dual-control appeal resolution requires second-level human approval")
        if not p.locked_payload_sha256: raise ReviewConflictError("appeal decision packet must be hash-locked")
        old=self.post.history(claim_id); supersedes=old[-1] if old else None; now=_now(); provenance={"original_decision_id":a.original_decision_id,"original_packet_id":a.original_packet_id,"appeal_id":appeal_id,"appeal_snapshot_id":p.snapshot_id,"appeal_snapshot_sha256":p.snapshot_sha256,"recommendation_run_id":p.recommendation_run_id,"citation_refs":p.citation_refs,"comparison_refs":p.resolved_comparison_refs,"annotation_refs":p.annotation_refs,"checkpoint_refs":p.checkpoint_refs,"primary_reviewer":p.primary_reviewer_user_id,"second_reviewer":p.second_reviewer_user_id,"human_only":True}
        payload={"packet_locked_sha256":p.locked_payload_sha256,"outcome":p.outcome,"decision":p.controlling_decision,"original_amount":str(p.original_approved_amount),"reconsidered_amount":str(p.reconsidered_approved_amount),"financial_delta":str(p.financial_delta),"provenance":provenance}
        row=self.repo.add(AppealFinalResolutionModel(resolution_id=f"afr_{uuid4().hex}",tenant_id=self.tenant_id,claim_id=claim_id,appeal_id=appeal_id,packet_id=packet_id,primary_reviewer_user_id=reviewer_user_id,second_reviewer_user_id=p.second_reviewer_user_id,outcome=p.outcome,controlling_decision=p.controlling_decision,original_approved_amount=p.original_approved_amount,reconsidered_approved_amount=p.reconsidered_approved_amount,financial_delta=p.financial_delta,reconsideration_snapshot_sha256=p.snapshot_sha256,packet_locked_sha256=p.locked_payload_sha256,provenance=provenance,payload_sha256=_sha(payload),supersedes_history_version_id=None if supersedes is None else supersedes.history_version_id,history_version_id=None,notice_id=None,idempotency_key=idempotency_key,trace_id=trace_id,resolved_at=now))
        original=self._original_packet(a);postsvc=PostDecisionService(self.session,self.tenant_id);hist=postsvc._history(original,source_type="appeal_final_resolution",source_id=row.resolution_id,decision=row.controlling_decision,human_reviewer_user_id=reviewer_user_id,evidence_snapshot_sha256=p.snapshot_sha256,effective_at=now,payload={**payload,"resolution_id":row.resolution_id});row.history_version_id=hist.history_version_id
        for cp in self.reconsider.checkpoints(appeal_id):
            if cp.status!=AppealCheckpointStatus.CLOSED.value: cp.status=AppealCheckpointStatus.CLOSED.value;cp.requires_human_action=False;cp.resumed_by_user_id=reviewer_user_id;cp.resumed_at=now
        a.status=AppealStatus.RESOLVED.value;a.resolved_at=now;a.appeal_version+=1;a.updated_at=now;postsvc._complete_tasks(appeal_id=appeal_id)
        p.status="closed";p.final_resolution_id=row.resolution_id;p.closed_at=now;p.updated_at=now
        notice=self._create_notice(original,a,p,row,reviewer_user_id,trace_id);row.notice_id=notice.notice_id
        postsvc._task(claim_id,PostDecisionTaskType.NOTICE_RELEASE.value,_now()+timedelta(hours=int(postsvc.policy.get("notice_release_sla_hours",24))),f"appeal-final-notice-release-task:{notice.notice_id}",notice_id=notice.notice_id,appeal_id=appeal_id,assigned=reviewer_user_id,priority=90)
        postsvc._emit(claim_id,"communication.notice.drafted","decision_notice",notice.notice_id,{"status":notice.status,"notice_id":notice.notice_id,"appeal_id":appeal_id,"resolution_id":row.resolution_id,"audience":notice.audience},trace_id=trace_id)
        self._audit(claim_id,appeal_id,p.packet_id,"appeal_final_human_resolution_closed",reviewer_user_id,{"resolution_id":row.resolution_id,"history_version_id":hist.history_version_id,"notice_id":notice.notice_id,"controlling_decision":row.controlling_decision,"reconsidered_amount":str(row.reconsidered_approved_amount)},f"audit:{idempotency_key}",trace_id);self._emit(claim_id,"appeal.resolution.closed",appeal_id,{"appeal_id":appeal_id,"packet_id":p.packet_id,"status":"closed","resolution_id":row.resolution_id,"notice_id":notice.notice_id},trace_id);return row
    def _create_notice(self,original,a,p,row,actor_id,trace_id):
        existing=self.session.scalar(select(DecisionNoticeModel).where(DecisionNoticeModel.tenant_id==self.tenant_id,DecisionNoticeModel.resolution_id==row.resolution_id))
        if existing:return existing
        explanations=[{"reason_code":c,"explanation":REASON_CODE_EXPLANATIONS.get(c,REASON_CODE_EXPLANATIONS["other"])} for c in p.reason_codes];payload={"claim_id":p.claim_id,"decision":p.controlling_decision,"approved_amount":str(p.reconsidered_approved_amount),"financial_change":str(p.financial_delta),"audience":"patient","decision_summary":f"Authorized human appeal review recorded the controlling outcome: {p.controlling_decision.replace('_',' ')}.","reason_explanations":explanations,"reconsideration_evidence_snapshot_reference":p.snapshot_sha256,"appeal_id":a.appeal_id,"resolution_id":row.resolution_id,"supersedes_original_decision_id":a.original_decision_id,"human_authority_statement":"Only authorized human appeal reviewers created this controlling outcome; AI/RAG/agents provided recommendation-only decision support."};now=_now()
        return self.post.add(DecisionNoticeModel(notice_id=f"notice_{uuid4().hex}",tenant_id=self.tenant_id,claim_id=p.claim_id,packet_id=original.packet_id,decision_id=original.decision_id,appeal_id=a.appeal_id,resolution_id=row.resolution_id,template_key="medical_claim_appeal_resolution_notice",template_version="2.0.0",notice_version=2,audience="patient",status=DecisionNoticeStatus.DRAFT.value,reason_explanations=explanations,rendered_payload=payload,rendered_payload_sha256=_sha(payload),evidence_snapshot_sha256=p.snapshot_sha256,locked_decision_payload_sha256=p.locked_payload_sha256,generated_by_actor_type="deterministic_human_resolution_renderer",generated_by_actor_id=actor_id,released_by_user_id=None,idempotency_key=f"appeal-final-notice:{row.resolution_id}",trace_id=trace_id,created_at=now,updated_at=now,released_at=None))
    def snapshot(self,claim_id,appeal_id):
        a=self._appeal(claim_id,appeal_id);p=self.repo.latest_packet(appeal_id);r=self.repo.final_resolution(appeal_id);reviews=[] if p is None else self.repo.second_reviews(p.packet_id);audit=self.repo.audit(appeal_id);history=self.post.history(claim_id)
        return {"claim_id":claim_id,"appeal_id":appeal_id,"appeal_status":a.status,"appeal_version":a.appeal_version,"packet":None if p is None else self.packet_view(p),"second_reviews":[{"second_review_id":x.second_review_id,"reviewer_user_id":x.reviewer_user_id,"action":x.action,"rationale":x.rationale,"payload_sha256":x.payload_sha256,"created_at":x.created_at} for x in reviews],"final_resolution":None if r is None else {"resolution_id":r.resolution_id,"outcome":r.outcome,"controlling_decision":r.controlling_decision,"original_approved_amount":str(r.original_approved_amount),"reconsidered_approved_amount":str(r.reconsidered_approved_amount),"financial_delta":str(r.financial_delta),"history_version_id":r.history_version_id,"notice_id":r.notice_id,"payload_sha256":r.payload_sha256,"resolved_at":r.resolved_at},"supersession_chain":[{"sequence":x.sequence,"source_type":x.source_type,"source_id":x.source_id,"decision":x.decision,"previous_version_sha256":x.previous_version_sha256,"version_sha256":x.version_sha256} for x in history],"audit_chain":[{"sequence":x.sequence,"event_type":x.event_type,"actor_id":x.actor_id,"previous_event_sha256":x.previous_event_sha256,"event_sha256":x.event_sha256,"occurred_at":x.occurred_at} for x in audit],"traceability":self.traceability(claim_id,appeal_id),"authority":{"llm":False,"langgraph":False,"rag":False,"mcp":False,"automation":False,"authorized_human_reviewers_required":True}}
    def traceability(self,claim_id,appeal_id):
        a=self._appeal(claim_id,appeal_id); original=self._original_packet(a); snap=self.reconsider.latest_snapshot(appeal_id); p=self.repo.latest_packet(appeal_id); final=self.repo.final_resolution(appeal_id); nodes=[];edges=[]
        nodes.append({"id":original.packet_id,"type":"original_locked_human_decision_packet","decision":original.decision,"sha256":original.locked_payload_sha256})
        nodes.append({"id":a.appeal_id,"type":"appeal","status":a.status});edges.append({"from":original.packet_id,"to":a.appeal_id,"relationship":"appealed"})
        if snap:
            nodes.append({"id":snap.snapshot_id,"type":"immutable_reconsideration_snapshot","sha256":snap.snapshot_sha256});edges.append({"from":a.appeal_id,"to":snap.snapshot_id,"relationship":"binds_original_and_supplemental_evidence"})
        for rec in self.reconsider.recommendations(appeal_id):
            nodes.append({"id":rec.reconsideration_run_id,"type":"recommendation_only_agent","authority":"none"});
            if snap: edges.append({"from":snap.snapshot_id,"to":rec.reconsideration_run_id,"relationship":"supports_nonbinding_recommendation"})
        if p:
            nodes.append({"id":p.packet_id,"type":"locked_human_appeal_decision_packet","status":p.status,"sha256":p.locked_payload_sha256});
            if snap: edges.append({"from":snap.snapshot_id,"to":p.packet_id,"relationship":"evidence_and_citations_bound_to_human_packet"})
            if p.recommendation_run_id:edges.append({"from":p.recommendation_run_id,"to":p.packet_id,"relationship":"recommendation_compared_with_human_judgment"})
        if final:
            nodes.append({"id":final.resolution_id,"type":"controlling_human_appeal_resolution","decision":final.controlling_decision,"sha256":final.payload_sha256});edges.append({"from":p.packet_id if p else a.appeal_id,"to":final.resolution_id,"relationship":"closed_by_authorized_human_dual_control_when_required"})
            if final.notice_id:nodes.append({"id":final.notice_id,"type":"reconsideration_notice"});edges.append({"from":final.resolution_id,"to":final.notice_id,"relationship":"rendered_for_separate_human_release_and_transport"})
        return {"nodes":nodes,"edges":edges,"original_decision_immutable":True,"controlling_outcome_human_only":True,"complete_original_to_final_lineage":True}
    def packet_view(self,p): return {"packet_id":p.packet_id,"status":p.status,"packet_version":p.packet_version,"primary_reviewer_user_id":p.primary_reviewer_user_id,"second_reviewer_user_id":p.second_reviewer_user_id,"snapshot_id":p.snapshot_id,"snapshot_sha256":p.snapshot_sha256,"recommendation_run_id":p.recommendation_run_id,"outcome":p.outcome,"controlling_decision":p.controlling_decision,"rationale":p.rationale,"reason_codes":p.reason_codes,"citation_refs":p.citation_refs,"resolved_comparison_refs":p.resolved_comparison_refs,"original_approved_amount":str(p.original_approved_amount),"reconsidered_approved_amount":str(p.reconsidered_approved_amount),"financial_delta":str(p.financial_delta),"material_financial_change":p.material_financial_change,"recommendation_disagreement":p.recommendation_disagreement,"recommendation_disagreement_reason":p.recommendation_disagreement_reason,"completeness":p.completeness,"blocker_codes":p.blocker_codes,"dual_control_required":p.dual_control_required,"locked_payload_sha256":p.locked_payload_sha256,"final_resolution_id":p.final_resolution_id}
