from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.claims import HumanDecision
from app.domain.post_decision import AppealResolutionOutcome, AppealStatus, DecisionNoticeStatus, PostDecisionTaskType, REASON_CODE_EXPLANATIONS
from app.domain.realtime import EventEnvelope, EventTopic
from app.models.claims import EvidenceArtifactModel
from app.models.governed_closure import DecisionNotificationIntentModel, ReviewDecisionPacketModel
from app.models.post_decision import (
    AppealCaseModel, AppealReviewAssignmentModel, AppealResolutionModel, AppealSupplementalEvidenceModel,
    CommunicationDeadLetterModel, CommunicationDeliveryAttemptModel, DecisionHistoryVersionModel,
    DecisionNoticeModel, ExternalCorrespondenceModel, PostDecisionTaskModel,
)
from app.repositories.governed_closure import GovernedClosureRepository
from app.repositories.post_decision import PostDecisionRepository
from app.repositories.tenancy import MembershipRepository
from app.realtime.events import enqueue_realtime_event
from app.services.review_workbench import ReviewConflictError


def _now() -> datetime:
    return datetime.now(UTC)


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _sha(value: object) -> str:
    raw=value if isinstance(value,str) else _canonical(value)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# Import-safe constant kept local because Release 36 must remain deterministic and
# must not invoke an LLM to determine appeal rights, deadlines, or final outcomes.
FINAL_DECISIONS=frozenset({"approve","deny","partial_approve"})


class PostDecisionService:
    """Human-governed communications and appeals lifecycle.

    Automation may render deterministic drafts, enqueue delivery, retry transport,
    and surface SLA tasks. Only authenticated claims reviewers may release notices,
    reopen appeals, or persist reconsideration resolutions. Original adjudication
    records are never updated or deleted by this service.
    """

    def __init__(self, session: Session, tenant_id: str):
        self.session=session; self.tenant_id=tenant_id
        self.repo=PostDecisionRepository(session,tenant_id)
        self.closure=GovernedClosureRepository(session,tenant_id)
        self.policy=self._load_policy()

    @staticmethod
    def _load_policy() -> dict:
        path=Path(__file__).resolve().parents[3]/"config"/"post_decision_communications_policy.json"
        try: return json.loads(path.read_text())
        except Exception:
            return {"appeal_window_days":180,"appeal_triage_sla_hours":24,"appeal_review_sla_hours":120,"notice_release_sla_hours":24,"max_delivery_attempts":3,"decision_notice_template":{"template_key":"medical_claim_decision_notice","template_version":"1.0.0"}}

    def _require_reviewer(self,user_id:str) -> None:
        membership=MembershipRepository(self.session,self.tenant_id).get_by_user(user_id)
        if membership is None or membership.status!="active" or membership.role!="claims_reviewer":
            raise ReviewConflictError("active human claims reviewer membership required")

    def _closed_packet(self,claim_id:str,packet_id:str) -> ReviewDecisionPacketModel:
        packet=self.closure.get_packet(packet_id)
        if packet is None or packet.claim_id!=claim_id: raise LookupError("governed decision packet not found")
        if packet.status!="closed" or not packet.decision_id or packet.decision not in FINAL_DECISIONS:
            raise ReviewConflictError("post-decision operations require a closed human financial decision packet")
        if not packet.locked_payload_sha256 or not packet.evidence_snapshot_sha256:
            raise ReviewConflictError("closed decision packet is missing immutable evidence binding")
        return packet

    def _emit(self,claim_id:str,event_type:str,aggregate_type:str,aggregate_id:str,metadata:dict,*,trace_id:str|None=None):
        safe={k:v for k,v in metadata.items() if k in {"status","notice_id","appeal_id","resolution_id","due_at","task_type","audience","delivery_status"}}
        return enqueue_realtime_event(self.session,envelope=EventEnvelope(
            event_id=f"pde_{uuid4().hex}",event_type=event_type,tenant_id=self.tenant_id,claim_id=claim_id,
            aggregate_type=aggregate_type,aggregate_id=aggregate_id,occurred_at=_now(),trace_id=trace_id,
            producer="medclaimiq-post-decision",payload=metadata,metadata=safe,
        ),topic=EventTopic.CLAIMS.value)

    def _task(self,claim_id:str,task_type:str,due_at:datetime,idempotency_key:str,*,appeal_id:str|None=None,notice_id:str|None=None,assigned:str|None=None,priority:int=50):
        existing=self.session.scalar(select(PostDecisionTaskModel).where(PostDecisionTaskModel.tenant_id==self.tenant_id,PostDecisionTaskModel.idempotency_key==idempotency_key))
        if existing: return existing
        return self.repo.add(PostDecisionTaskModel(
            task_id=f"pdt_{uuid4().hex}",tenant_id=self.tenant_id,claim_id=claim_id,appeal_id=appeal_id,notice_id=notice_id,
            task_type=task_type,status="open",priority=priority,assigned_reviewer_user_id=assigned,due_at=due_at,
            breached_at=None,completed_at=None,idempotency_key=idempotency_key,created_at=_now(),
        ))

    def _complete_tasks(self,*,notice_id:str|None=None,appeal_id:str|None=None,task_type:str|None=None):
        stmt=select(PostDecisionTaskModel).where(PostDecisionTaskModel.tenant_id==self.tenant_id,PostDecisionTaskModel.status=="open")
        if notice_id: stmt=stmt.where(PostDecisionTaskModel.notice_id==notice_id)
        if appeal_id: stmt=stmt.where(PostDecisionTaskModel.appeal_id==appeal_id)
        if task_type: stmt=stmt.where(PostDecisionTaskModel.task_type==task_type)
        now=_now()
        for row in self.session.scalars(stmt): row.status="completed"; row.completed_at=now

    def _history(self,packet:ReviewDecisionPacketModel,*,source_type:str,source_id:str,decision:str,human_reviewer_user_id:str,evidence_snapshot_sha256:str,effective_at:datetime,payload:dict) -> DecisionHistoryVersionModel:
        existing=self.session.scalar(select(DecisionHistoryVersionModel).where(DecisionHistoryVersionModel.tenant_id==self.tenant_id,DecisionHistoryVersionModel.source_type==source_type,DecisionHistoryVersionModel.source_id==source_id))
        if existing: return existing
        prior=self.repo.history(packet.claim_id); previous=prior[-1].version_sha256 if prior else None
        sequence=self.repo.next_history_sequence(packet.claim_id); payload_sha=_sha(payload)
        version_sha=_sha({"tenant_id":self.tenant_id,"claim_id":packet.claim_id,"sequence":sequence,"source_type":source_type,"source_id":source_id,"decision":decision,"reviewer":human_reviewer_user_id,"evidence_snapshot_sha256":evidence_snapshot_sha256,"previous_version_sha256":previous,"version_payload_sha256":payload_sha,"effective_at":effective_at})
        return self.repo.add(DecisionHistoryVersionModel(
            history_version_id=f"dhv_{uuid4().hex}",tenant_id=self.tenant_id,claim_id=packet.claim_id,sequence=sequence,
            source_type=source_type,source_id=source_id,decision=decision,human_reviewer_user_id=human_reviewer_user_id,
            evidence_snapshot_sha256=evidence_snapshot_sha256,previous_version_sha256=previous,version_payload_sha256=payload_sha,
            version_sha256=version_sha,effective_at=effective_at,
        ))

    def _original_history(self,packet:ReviewDecisionPacketModel):
        return self._history(packet,source_type="original_decision",source_id=packet.decision_id,decision=packet.decision,
            human_reviewer_user_id=packet.primary_reviewer_user_id,evidence_snapshot_sha256=packet.evidence_snapshot_sha256,
            effective_at=packet.closed_at or _now(),payload={"packet_id":packet.packet_id,"decision_id":packet.decision_id,"locked_payload_sha256":packet.locked_payload_sha256,"reason_codes":packet.reason_codes})

    def _notice_payload(self,packet:ReviewDecisionPacketModel,*,audience:str,appeal_id:str|None=None,resolution:AppealResolutionModel|None=None) -> dict:
        decision=resolution.controlling_decision if resolution else packet.decision
        reason_codes=resolution.reason_codes if resolution else packet.reason_codes
        explanations=[{"reason_code":code,"explanation":REASON_CODE_EXPLANATIONS.get(code,REASON_CODE_EXPLANATIONS["other"])} for code in reason_codes]
        return {
            "claim_id":packet.claim_id,"decision":decision,"audience":audience,
            "decision_summary":f"An authorized human reviewer recorded the claim outcome: {decision.replace('_',' ')}.",
            "reason_explanations":explanations,"evidence_snapshot_reference":packet.evidence_snapshot_sha256,
            "appeal_rights":{"appeal_window_days":int(self.policy.get("appeal_window_days",180)),"instructions":"Submit an appeal through the authenticated claim portal and provide any supplemental evidence through the secure evidence workflow."},
            "human_authority_statement":"AI may assist with evidence organization or drafting, but this outcome was issued by an authorized human reviewer.",
            "original_decision_id":packet.decision_id,"appeal_id":appeal_id,"resolution_id":None if resolution is None else resolution.resolution_id,
        }

    def create_notice(self,claim_id:str,packet_id:str,actor_id:str,*,audience:str="patient",idempotency_key:str,trace_id:str|None=None,appeal_id:str|None=None,resolution:AppealResolutionModel|None=None) -> DecisionNoticeModel:
        existing=self.session.scalar(select(DecisionNoticeModel).where(DecisionNoticeModel.tenant_id==self.tenant_id,DecisionNoticeModel.idempotency_key==idempotency_key))
        if existing: return existing
        packet=self._closed_packet(claim_id,packet_id); self._original_history(packet)
        payload=self._notice_payload(packet,audience=audience,appeal_id=appeal_id,resolution=resolution)
        template=self.policy.get("decision_notice_template",{})
        row=self.repo.add(DecisionNoticeModel(
            notice_id=f"notice_{uuid4().hex}",tenant_id=self.tenant_id,claim_id=claim_id,packet_id=packet.packet_id,decision_id=packet.decision_id,
            appeal_id=appeal_id,resolution_id=None if resolution is None else resolution.resolution_id,
            template_key=template.get("template_key","medical_claim_decision_notice"),template_version=template.get("template_version","1.0.0"),notice_version=1,
            audience=audience,status=DecisionNoticeStatus.DRAFT.value,reason_explanations=payload["reason_explanations"],rendered_payload=payload,
            rendered_payload_sha256=_sha(payload),evidence_snapshot_sha256=packet.evidence_snapshot_sha256,locked_decision_payload_sha256=packet.locked_payload_sha256,
            generated_by_actor_type="human_or_deterministic_system",generated_by_actor_id=actor_id,released_by_user_id=None,
            idempotency_key=idempotency_key,trace_id=trace_id,created_at=_now(),updated_at=_now(),released_at=None,
        ))
        self._task(claim_id,PostDecisionTaskType.NOTICE_RELEASE.value,_now()+timedelta(hours=int(self.policy.get("notice_release_sla_hours",24))),f"notice-release-task:{row.notice_id}",notice_id=row.notice_id,priority=70)
        self._emit(claim_id,"communication.notice.drafted","decision_notice",row.notice_id,{"status":row.status,"notice_id":row.notice_id,"audience":audience},trace_id=trace_id)
        return row

    def bootstrap_after_closure(self,packet:ReviewDecisionPacketModel,actor_id:str,*,trace_id:str|None=None) -> DecisionNoticeModel | None:
        if packet.status!="closed" or packet.decision not in FINAL_DECISIONS or not packet.decision_id: return None
        return self.create_notice(packet.claim_id,packet.packet_id,actor_id,audience="patient",idempotency_key=f"post-close-notice:{packet.decision_id}",trace_id=trace_id)

    def release_notice(self,claim_id:str,notice_id:str,reviewer_user_id:str,*,idempotency_key:str,trace_id:str|None=None) -> DecisionNoticeModel:
        self._require_reviewer(reviewer_user_id); row=self.repo.notice(notice_id,for_update=True)
        if row is None or row.claim_id!=claim_id: raise LookupError("decision notice not found")
        if row.status in {DecisionNoticeStatus.RELEASED.value,DecisionNoticeStatus.DELIVERY_PENDING.value,DecisionNoticeStatus.DELIVERED.value}: return row
        if row.status!=DecisionNoticeStatus.DRAFT.value: raise ReviewConflictError("only a deterministic draft notice can be human-released")
        if row.rendered_payload_sha256!=_sha(row.rendered_payload): raise ReviewConflictError("decision notice payload changed after generation")
        packet=self._closed_packet(claim_id,row.packet_id)
        if row.resolution_id and str(row.resolution_id).startswith("afr_"):
            from app.models.appeal_resolution import AppealFinalResolutionModel
            final_resolution=self.session.scalar(select(AppealFinalResolutionModel).where(AppealFinalResolutionModel.tenant_id==self.tenant_id,AppealFinalResolutionModel.resolution_id==row.resolution_id))
            if final_resolution is None or final_resolution.appeal_id!=row.appeal_id:
                raise ReviewConflictError("appeal resolution notice is not bound to a final human appeal resolution")
            if row.locked_decision_payload_sha256!=final_resolution.packet_locked_sha256 or row.evidence_snapshot_sha256!=final_resolution.reconsideration_snapshot_sha256:
                raise ReviewConflictError("appeal resolution notice no longer matches the locked reconsideration decision/evidence snapshot")
        elif row.locked_decision_payload_sha256!=packet.locked_payload_sha256 or row.evidence_snapshot_sha256!=packet.evidence_snapshot_sha256:
            raise ReviewConflictError("decision notice no longer matches the locked adjudication snapshot")
        now=_now(); row.status=DecisionNoticeStatus.DELIVERY_PENDING.value; row.released_by_user_id=reviewer_user_id; row.released_at=now; row.updated_at=now
        key=f"decision-notice-delivery:{row.notice_id}:{row.audience}"
        existing=self.session.scalar(select(DecisionNotificationIntentModel).where(DecisionNotificationIntentModel.tenant_id==self.tenant_id,DecisionNotificationIntentModel.idempotency_key==key))
        if not existing:
            self.closure.add(DecisionNotificationIntentModel(notification_id=f"dni_{uuid4().hex}",tenant_id=self.tenant_id,claim_id=claim_id,packet_id=row.packet_id,audience=row.audience,notification_type="decision_notice_delivery",status="pending_delivery",payload_sha256=row.rendered_payload_sha256,idempotency_key=key,created_at=now,delivered_at=None))
        self._complete_tasks(notice_id=row.notice_id,task_type=PostDecisionTaskType.NOTICE_RELEASE.value)
        self._task(claim_id,PostDecisionTaskType.NOTICE_DELIVERY.value,now+timedelta(hours=24),f"notice-delivery-task:{row.notice_id}",notice_id=row.notice_id,priority=60)
        self.record_correspondence(claim_id,reviewer_user_id,direction="outbound",channel="portal",audience=row.audience,payload_sha256=row.rendered_payload_sha256,idempotency_key=f"notice-release-correspondence:{idempotency_key}",notice_id=row.notice_id,appeal_id=row.appeal_id,external_message_id=None,actor_type="human")
        self._emit(claim_id,"communication.notice.released","decision_notice",row.notice_id,{"status":row.status,"notice_id":row.notice_id,"audience":row.audience,"delivery_status":"pending_delivery"},trace_id=trace_id)
        # Release 37: transport provisioning is bounded to the already human-released
        # artifact. Missing approved templates/endpoints create operational incidents;
        # they never change or manufacture an adjudication outcome.
        from app.services.communication_delivery import CommunicationDeliveryService
        CommunicationDeliveryService(self.session,self.tenant_id).queue_released_notice(
            row.notice_id,idempotency_key=f"auto-transport:{row.notice_id}",trace_id=trace_id
        )
        return row

    def submit_appeal(self,claim_id:str,submitter_actor_id:str,submitter_actor_type:str,*,notice_id:str,grounds:list[str],statement:str,late_filing_reason:str|None,idempotency_key:str,trace_id:str|None=None) -> AppealCaseModel:
        existing=self.session.scalar(select(AppealCaseModel).where(AppealCaseModel.tenant_id==self.tenant_id,AppealCaseModel.idempotency_key==idempotency_key))
        if existing:return existing
        notice=self.repo.notice(notice_id)
        if notice is None or notice.claim_id!=claim_id: raise LookupError("released decision notice not found")
        if notice.status not in {DecisionNoticeStatus.DELIVERY_PENDING.value,DecisionNoticeStatus.DELIVERED.value,DecisionNoticeStatus.RELEASED.value} or notice.released_at is None:
            raise ReviewConflictError("appeal intake requires a human-released decision notice")
        packet=self._closed_packet(claim_id,notice.packet_id); now=_now(); due=notice.released_at+timedelta(days=int(self.policy.get("appeal_window_days",180)))
        if submitter_actor_type not in {"patient","provider","hospital_admin","authorized_representative"}: raise ReviewConflictError("appeal submitter must be an authorized external claim participant")
        if now>due and not late_filing_reason: status=AppealStatus.REJECTED_UNTIMELY.value
        elif now>due: status=AppealStatus.LATE_PENDING_REVIEW.value
        else: status=AppealStatus.SUBMITTED.value
        row=self.repo.add(AppealCaseModel(
            appeal_id=f"appeal_{uuid4().hex}",tenant_id=self.tenant_id,claim_id=claim_id,original_packet_id=packet.packet_id,original_decision_id=packet.decision_id,
            notice_id=notice.notice_id,status=status,submitter_actor_type=submitter_actor_type,submitter_actor_id=submitter_actor_id,grounds=list(dict.fromkeys(grounds)),statement=statement,
            late_filing_reason=late_filing_reason,appeal_due_at=due,submitted_at=now,assigned_reviewer_user_id=None,appeal_version=1,reopened_at=None,resolved_at=None,
            idempotency_key=idempotency_key,trace_id=trace_id,created_at=now,updated_at=now,
        ))
        if status!=AppealStatus.REJECTED_UNTIMELY.value:
            self._task(claim_id,PostDecisionTaskType.APPEAL_TRIAGE.value,now+timedelta(hours=int(self.policy.get("appeal_triage_sla_hours",24))),f"appeal-triage-task:{row.appeal_id}",appeal_id=row.appeal_id,priority=90 if status==AppealStatus.LATE_PENDING_REVIEW.value else 80)
        self.record_correspondence(claim_id,submitter_actor_id,direction="inbound",channel="portal",audience="payer_appeals",payload_sha256=_sha({"grounds":grounds,"statement":statement,"late_filing_reason":late_filing_reason}),idempotency_key=f"appeal-intake-correspondence:{idempotency_key}",notice_id=notice_id,appeal_id=row.appeal_id,external_message_id=None,actor_type=submitter_actor_type)
        self._emit(claim_id,"appeal.submitted","appeal",row.appeal_id,{"status":row.status,"appeal_id":row.appeal_id,"due_at":due.isoformat()},trace_id=trace_id)
        return row

    def link_supplemental_evidence(self,claim_id:str,appeal_id:str,evidence_id:str,actor_id:str,actor_type:str,*,idempotency_key:str,trace_id:str|None=None) -> AppealSupplementalEvidenceModel:
        appeal=self.repo.appeal(appeal_id,for_update=True)
        if appeal is None or appeal.claim_id!=claim_id: raise LookupError("appeal not found")
        if appeal.status in {AppealStatus.RESOLVED.value,AppealStatus.WITHDRAWN.value,AppealStatus.REJECTED_UNTIMELY.value}: raise ReviewConflictError("appeal no longer accepts supplemental evidence")
        existing=self.session.scalar(select(AppealSupplementalEvidenceModel).where(AppealSupplementalEvidenceModel.tenant_id==self.tenant_id,AppealSupplementalEvidenceModel.appeal_id==appeal_id,AppealSupplementalEvidenceModel.evidence_id==evidence_id))
        if existing:return existing
        evidence=self.session.scalar(select(EvidenceArtifactModel).where(EvidenceArtifactModel.tenant_id==self.tenant_id,EvidenceArtifactModel.claim_id==claim_id,EvidenceArtifactModel.evidence_id==evidence_id))
        if evidence is None: raise ReviewConflictError("supplemental evidence must belong to the appealed claim")
        if evidence.status!="ready": raise ReviewConflictError("supplemental evidence must complete quarantine and processing before appeal use")
        row=self.repo.add(AppealSupplementalEvidenceModel(link_id=f"ase_{uuid4().hex}",tenant_id=self.tenant_id,claim_id=claim_id,appeal_id=appeal_id,evidence_id=evidence_id,evidence_version=evidence.evidence_version,content_sha256=evidence.content_sha256,linked_by_actor_type=actor_type,linked_by_actor_id=actor_id,linked_at=_now()))
        appeal.appeal_version+=1; appeal.updated_at=_now()
        if appeal.assigned_reviewer_user_id:
            self._task(claim_id,PostDecisionTaskType.SUPPLEMENTAL_EVIDENCE_REVIEW.value,_now()+timedelta(hours=24),f"appeal-supplemental-task:{row.link_id}",appeal_id=appeal_id,assigned=appeal.assigned_reviewer_user_id,priority=75)
        self._emit(claim_id,"appeal.evidence.linked","appeal",appeal_id,{"status":appeal.status,"appeal_id":appeal_id},trace_id=trace_id)
        # Release 38: register the accepted evidence with the appeal-specific re-ingestion
        # pipeline. Registration is metadata-only and cannot change claim adjudication.
        from app.services.appeal_reconsideration import AppealReconsiderationService
        AppealReconsiderationService(self.session,self.tenant_id).register_linked_evidence(claim_id,appeal_id,evidence_id,trace_id=trace_id)
        return row

    def assign_appeal(self,claim_id:str,appeal_id:str,assigner_user_id:str,reviewer_user_id:str,*,assignment_reason:str,expected_appeal_version:int,idempotency_key:str,trace_id:str|None=None) -> AppealCaseModel:
        self._require_reviewer(assigner_user_id); self._require_reviewer(reviewer_user_id)
        appeal=self.repo.appeal(appeal_id,for_update=True)
        if appeal is None or appeal.claim_id!=claim_id: raise LookupError("appeal not found")
        if appeal.appeal_version!=expected_appeal_version: raise ReviewConflictError("appeal version conflict")
        packet=self._closed_packet(claim_id,appeal.original_packet_id)
        disallowed={packet.primary_reviewer_user_id,packet.second_reviewer_user_id}
        if reviewer_user_id in disallowed: raise ReviewConflictError("appeal reviewer must be independent from original adjudication reviewers")
        prior=self.session.scalar(select(AppealReviewAssignmentModel).where(AppealReviewAssignmentModel.tenant_id==self.tenant_id,AppealReviewAssignmentModel.appeal_id==appeal_id,AppealReviewAssignmentModel.reviewer_user_id==reviewer_user_id))
        if not prior:
            self.repo.add(AppealReviewAssignmentModel(assignment_id=f"ara_{uuid4().hex}",tenant_id=self.tenant_id,appeal_id=appeal_id,claim_id=claim_id,reviewer_user_id=reviewer_user_id,assigned_by_actor_type="human",assigned_by_actor_id=assigner_user_id,independence_verified=True,assignment_reason=assignment_reason,assigned_at=_now()))
        appeal.assigned_reviewer_user_id=reviewer_user_id; appeal.appeal_version+=1; appeal.status=AppealStatus.TRIAGE.value if appeal.status!=AppealStatus.REJECTED_UNTIMELY.value else appeal.status; appeal.updated_at=_now()
        self._complete_tasks(appeal_id=appeal_id,task_type=PostDecisionTaskType.APPEAL_TRIAGE.value)
        self._task(claim_id,PostDecisionTaskType.APPEAL_REVIEW.value,_now()+timedelta(hours=int(self.policy.get("appeal_review_sla_hours",120))),f"appeal-review-task:{appeal_id}:{appeal.appeal_version}",appeal_id=appeal_id,assigned=reviewer_user_id,priority=85)
        self._emit(claim_id,"appeal.assigned","appeal",appeal_id,{"status":appeal.status,"appeal_id":appeal_id,"task_type":"appeal_review"},trace_id=trace_id)
        return appeal

    def reopen_appeal(self,claim_id:str,appeal_id:str,reviewer_user_id:str,*,expected_appeal_version:int,rationale:str,idempotency_key:str,trace_id:str|None=None) -> AppealCaseModel:
        self._require_reviewer(reviewer_user_id); appeal=self.repo.appeal(appeal_id,for_update=True)
        if appeal is None or appeal.claim_id!=claim_id: raise LookupError("appeal not found")
        if appeal.assigned_reviewer_user_id!=reviewer_user_id: raise ReviewConflictError("only the independent assigned appeal reviewer may reopen reconsideration")
        if appeal.appeal_version!=expected_appeal_version: raise ReviewConflictError("appeal version conflict")
        if appeal.status not in {AppealStatus.SUBMITTED.value,AppealStatus.LATE_PENDING_REVIEW.value,AppealStatus.TRIAGE.value,AppealStatus.WAITING_SUPPLEMENTAL_EVIDENCE.value}: raise ReviewConflictError("appeal is not eligible for controlled reopening")
        if appeal.status==AppealStatus.LATE_PENDING_REVIEW.value and not appeal.late_filing_reason: raise ReviewConflictError("late appeal requires documented filing reason")
        appeal.status=AppealStatus.IN_REVIEW.value; appeal.reopened_at=_now(); appeal.appeal_version+=1; appeal.updated_at=_now()
        self.record_correspondence(claim_id,reviewer_user_id,direction="outbound",channel="portal",audience="appeal_submitter",payload_sha256=_sha({"appeal_id":appeal_id,"status":"in_review","rationale":rationale}),idempotency_key=f"appeal-reopen-correspondence:{idempotency_key}",appeal_id=appeal_id,notice_id=appeal.notice_id,external_message_id=None,actor_type="human")
        self._emit(claim_id,"appeal.reopened","appeal",appeal_id,{"status":appeal.status,"appeal_id":appeal_id},trace_id=trace_id)
        return appeal

    def resolve_appeal(self,claim_id:str,appeal_id:str,reviewer_user_id:str,*,outcome:AppealResolutionOutcome,controlling_decision:HumanDecision,reason_codes:list[str],rationale:str,expected_appeal_version:int,idempotency_key:str,trace_id:str|None=None) -> AppealResolutionModel:
        # Release 39 hardening: this legacy service path is intentionally disabled.
        # Final appeal adjudication must use AppealResolutionService so the locked
        # reconsideration snapshot, citation/completeness checks, contradiction
        # blockers, optimistic concurrency and dual-control rules cannot be bypassed.
        raise ReviewConflictError("direct appeal resolution retired; use governed appeal resolution packets")

    def record_correspondence(self,claim_id:str,actor_id:str,*,direction:str,channel:str,audience:str,payload_sha256:str,idempotency_key:str,notice_id:str|None,appeal_id:str|None,external_message_id:str|None,actor_type:str="human") -> ExternalCorrespondenceModel:
        existing=self.session.scalar(select(ExternalCorrespondenceModel).where(ExternalCorrespondenceModel.tenant_id==self.tenant_id,ExternalCorrespondenceModel.idempotency_key==idempotency_key))
        if existing:return existing
        if notice_id:
            notice=self.repo.notice(notice_id)
            if notice is None or notice.claim_id!=claim_id: raise ReviewConflictError("correspondence notice must belong to claim")
        if appeal_id:
            appeal=self.repo.appeal(appeal_id)
            if appeal is None or appeal.claim_id!=claim_id: raise ReviewConflictError("correspondence appeal must belong to claim")
        return self.repo.add(ExternalCorrespondenceModel(correspondence_id=f"corr_{uuid4().hex}",tenant_id=self.tenant_id,claim_id=claim_id,appeal_id=appeal_id,notice_id=notice_id,direction=direction,channel=channel,audience=audience,external_message_id=external_message_id,payload_sha256=payload_sha256,actor_type=actor_type,actor_id=actor_id,idempotency_key=idempotency_key,occurred_at=_now()))

    def record_delivery_attempt(self,claim_id:str,notification_id:str,*,channel:str,success:bool,provider_message_id:str|None,error_code:str|None,error_detail:str|None,trace_id:str|None=None) -> dict:
        notification=self.session.scalar(select(DecisionNotificationIntentModel).where(DecisionNotificationIntentModel.tenant_id==self.tenant_id,DecisionNotificationIntentModel.claim_id==claim_id,DecisionNotificationIntentModel.notification_id==notification_id).with_for_update())
        if notification is None: raise LookupError("notification intent not found")
        attempts=self.repo.attempts(notification_id); number=len(attempts)+1; max_attempts=int(self.policy.get("max_delivery_attempts",3))
        if attempts and attempts[-1].success: return {"status":"delivered","attempt_count":len(attempts),"dead_lettered":False}
        if len(attempts)>=max_attempts: return {"status":"dead_lettered","attempt_count":len(attempts),"dead_lettered":True}
        row=self.repo.add(CommunicationDeliveryAttemptModel(attempt_id=f"cda_{uuid4().hex}",tenant_id=self.tenant_id,claim_id=claim_id,notification_id=notification_id,attempt_number=number,channel=channel,success=success,provider_message_id=provider_message_id,error_code=error_code,error_detail_sha256=_sha(error_detail) if error_detail else None,attempted_at=_now()))
        dead=False
        if success:
            notification.status="delivered"; notification.delivered_at=_now()
            self._complete_notice_delivery(notification)
        elif number>=max_attempts:
            notification.status="dead_lettered"; dead=True
            if not self.repo.dead_letter(notification_id):
                self.repo.add(CommunicationDeadLetterModel(dead_letter_id=f"cdl_{uuid4().hex}",tenant_id=self.tenant_id,claim_id=claim_id,notification_id=notification_id,reason_code=error_code or "delivery_failed",final_error_sha256=row.error_detail_sha256,attempt_count=number,created_at=_now()))
            notice=self._notice_for_notification(notification)
            if notice: notice.status=DecisionNoticeStatus.DEAD_LETTERED.value; notice.updated_at=_now()
        else: notification.status="retry_pending"
        self._emit(claim_id,"communication.delivery.updated","notification",notification_id,{"status":notification.status,"delivery_status":notification.status},trace_id=trace_id)
        return {"status":notification.status,"attempt_count":number,"dead_lettered":dead}

    def _notice_for_notification(self,notification:DecisionNotificationIntentModel):
        if notification.notification_type!="decision_notice_delivery": return None
        return self.session.scalar(select(DecisionNoticeModel).where(DecisionNoticeModel.tenant_id==self.tenant_id,DecisionNoticeModel.packet_id==notification.packet_id,DecisionNoticeModel.audience==notification.audience,DecisionNoticeModel.rendered_payload_sha256==notification.payload_sha256).order_by(DecisionNoticeModel.created_at.desc()).limit(1))

    def _complete_notice_delivery(self,notification:DecisionNotificationIntentModel):
        notice=self._notice_for_notification(notification)
        if notice:
            notice.status=DecisionNoticeStatus.DELIVERED.value; notice.updated_at=_now(); self._complete_tasks(notice_id=notice.notice_id,task_type=PostDecisionTaskType.NOTICE_DELIVERY.value)

    def evaluate_sla(self) -> dict:
        now=_now(); rows=self.repo.tasks(status="open",limit=1000); breached=[]
        for row in rows:
            if row.due_at<=now and row.breached_at is None:
                row.breached_at=now; row.priority=max(row.priority,95); breached.append(row.task_id)
                self._emit(row.claim_id,"sla.post_decision.breached","post_decision_task",row.task_id,{"status":"breached","task_type":row.task_type,"due_at":row.due_at.isoformat(),"appeal_id":row.appeal_id,"notice_id":row.notice_id})
        return {"evaluated":len(rows),"newly_breached":breached}

    def task_queue(self,*,mine:str|None=None,limit:int=100) -> list[dict]:
        now=_now(); rows=self.repo.tasks(mine=mine,status="open",limit=limit)
        return [{"task_id":x.task_id,"claim_id":x.claim_id,"appeal_id":x.appeal_id,"notice_id":x.notice_id,"task_type":x.task_type,"priority":x.priority,"assigned_reviewer_user_id":x.assigned_reviewer_user_id,"due_at":x.due_at,"sla_breached":bool(x.breached_at or x.due_at<=now)} for x in rows]

    def snapshot(self,claim_id:str) -> dict:
        notices=self.repo.notices(claim_id); appeals=self.repo.appeals(claim_id); history=self.repo.history(claim_id); corr=self.repo.correspondence(claim_id)
        return {
            "claim_id":claim_id,
            "notices":[self.notice_view(x) for x in notices],
            "appeals":[self.appeal_view(x) for x in appeals],
            "decision_history":[{"history_version_id":x.history_version_id,"sequence":x.sequence,"source_type":x.source_type,"source_id":x.source_id,"decision":x.decision,"human_reviewer_user_id":x.human_reviewer_user_id,"evidence_snapshot_sha256":x.evidence_snapshot_sha256,"previous_version_sha256":x.previous_version_sha256,"version_sha256":x.version_sha256,"effective_at":x.effective_at} for x in history],
            "correspondence":[{"correspondence_id":x.correspondence_id,"appeal_id":x.appeal_id,"notice_id":x.notice_id,"direction":x.direction,"channel":x.channel,"audience":x.audience,"external_message_id":x.external_message_id,"payload_sha256":x.payload_sha256,"actor_type":x.actor_type,"actor_id":x.actor_id,"occurred_at":x.occurred_at} for x in corr],
            "tasks":self.task_queue(limit=200),
            "traceability":self.traceability(claim_id),
            "human_authority":{"ai_can_draft":True,"llm_can_issue_or_overturn":False,"langgraph_can_issue_or_overturn":False,"rag_can_issue_or_overturn":False,"mcp_can_issue_or_overturn":False,"automated_financial_execution":False},
        }

    def notice_view(self,row:DecisionNoticeModel)->dict:
        notification=self.session.scalar(select(DecisionNotificationIntentModel).where(DecisionNotificationIntentModel.tenant_id==self.tenant_id,DecisionNotificationIntentModel.packet_id==row.packet_id,DecisionNotificationIntentModel.notification_type=="decision_notice_delivery",DecisionNotificationIntentModel.audience==row.audience,DecisionNotificationIntentModel.payload_sha256==row.rendered_payload_sha256).order_by(DecisionNotificationIntentModel.created_at.desc()).limit(1))
        attempts=[] if notification is None else self.repo.attempts(notification.notification_id)
        return {"notice_id":row.notice_id,"packet_id":row.packet_id,"decision_id":row.decision_id,"appeal_id":row.appeal_id,"resolution_id":row.resolution_id,"template_key":row.template_key,"template_version":row.template_version,"notice_version":row.notice_version,"audience":row.audience,"status":row.status,"reason_explanations":row.reason_explanations,"rendered_payload_sha256":row.rendered_payload_sha256,"evidence_snapshot_sha256":row.evidence_snapshot_sha256,"released_by_user_id":row.released_by_user_id,"released_at":row.released_at,"notification_id":None if notification is None else notification.notification_id,"delivery_status":None if notification is None else notification.status,"delivery_attempts":len(attempts),"created_at":row.created_at}

    def appeal_view(self,row:AppealCaseModel)->dict:
        supplemental=self.repo.supplemental(row.appeal_id); resolution=self.repo.resolution(row.appeal_id)
        if resolution is None:
            from app.models.appeal_resolution import AppealFinalResolutionModel
            release39=self.session.scalar(select(AppealFinalResolutionModel).where(AppealFinalResolutionModel.tenant_id==self.tenant_id,AppealFinalResolutionModel.appeal_id==row.appeal_id))
            resolution_view=None if release39 is None else {"resolution_id":release39.resolution_id,"reviewer_user_id":release39.primary_reviewer_user_id,"outcome":release39.outcome,"controlling_decision":release39.controlling_decision,"reason_codes":[],"payload_sha256":release39.payload_sha256,"resolved_at":release39.resolved_at}
        else:
            resolution_view={"resolution_id":resolution.resolution_id,"reviewer_user_id":resolution.reviewer_user_id,"outcome":resolution.outcome,"controlling_decision":resolution.controlling_decision,"reason_codes":resolution.reason_codes,"payload_sha256":resolution.payload_sha256,"resolved_at":resolution.resolved_at}
        return {"appeal_id":row.appeal_id,"notice_id":row.notice_id,"status":row.status,"grounds":row.grounds,"statement":row.statement,"late_filing_reason":row.late_filing_reason,"appeal_due_at":row.appeal_due_at,"submitted_at":row.submitted_at,"assigned_reviewer_user_id":row.assigned_reviewer_user_id,"appeal_version":row.appeal_version,"reopened_at":row.reopened_at,"resolved_at":row.resolved_at,"supplemental_evidence":[{"evidence_id":x.evidence_id,"evidence_version":x.evidence_version,"content_sha256":x.content_sha256,"linked_at":x.linked_at} for x in supplemental],"resolution":resolution_view}

    def traceability(self,claim_id:str)->dict:
        nodes=[]; edges=[]
        packets=list(self.session.scalars(select(ReviewDecisionPacketModel).where(ReviewDecisionPacketModel.tenant_id==self.tenant_id,ReviewDecisionPacketModel.claim_id==claim_id,ReviewDecisionPacketModel.status=="closed")))
        for packet in packets:
            for item in packet.evidence_snapshot or []:
                eid=item.get("evidence_id"); nodes.append({"id":eid,"type":"original_evidence","sha256":item.get("content_sha256")}); edges.append({"from":eid,"to":packet.packet_id,"relationship":"bound_to_original_decision"})
            nodes.append({"id":packet.packet_id,"type":"locked_human_decision_packet","decision":packet.decision});
            if packet.decision_id: nodes.append({"id":packet.decision_id,"type":"original_human_decision"}); edges.append({"from":packet.packet_id,"to":packet.decision_id,"relationship":"persisted_human_decision"})
        for notice in self.repo.notices(claim_id):
            nodes.append({"id":notice.notice_id,"type":"decision_notice","status":notice.status}); edges.append({"from":notice.packet_id,"to":notice.notice_id,"relationship":"communicated_from_locked_decision"})
        for appeal in self.repo.appeals(claim_id):
            nodes.append({"id":appeal.appeal_id,"type":"appeal","status":appeal.status}); edges.append({"from":appeal.notice_id,"to":appeal.appeal_id,"relationship":"appeals_released_notice"})
            for x in self.repo.supplemental(appeal.appeal_id): nodes.append({"id":x.evidence_id,"type":"appeal_supplemental_evidence","sha256":x.content_sha256}); edges.append({"from":x.evidence_id,"to":appeal.appeal_id,"relationship":"supplements_appeal"})
            resolution=self.repo.resolution(appeal.appeal_id)
            if resolution:
                nodes.append({"id":resolution.resolution_id,"type":"human_reconsideration_resolution","decision":resolution.controlling_decision}); edges.append({"from":appeal.appeal_id,"to":resolution.resolution_id,"relationship":"resolved_by_independent_human"})
            else:
                from app.models.appeal_resolution import AppealFinalResolutionModel
                final=self.session.scalar(select(AppealFinalResolutionModel).where(AppealFinalResolutionModel.tenant_id==self.tenant_id,AppealFinalResolutionModel.appeal_id==appeal.appeal_id))
                if final:
                    nodes.append({"id":final.resolution_id,"type":"governed_final_appeal_resolution","decision":final.controlling_decision,"snapshot_sha256":final.reconsideration_snapshot_sha256}); edges.append({"from":appeal.appeal_id,"to":final.resolution_id,"relationship":"closed_by_evidence_bound_dual_control_human_workflow"})
        return {"claim_id":claim_id,"nodes":nodes,"edges":edges,"original_evidence_to_original_decision_to_appeal_evidence_to_reconsideration":True,"original_decision_immutable":True,"final_resolution_human_only":True}
