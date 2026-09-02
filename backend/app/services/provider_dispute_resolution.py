from __future__ import annotations
import hashlib,json
from datetime import UTC,datetime
from decimal import Decimal
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.domain.provider_dispute_resolution import FINAL_OUTCOMES,SECOND_REVIEW_ACTIONS,MATERIAL_FINANCIAL_CHANGE_ABS,MATERIAL_FINANCIAL_CHANGE_PCT
from app.domain.realtime import EventEnvelope,EventTopic
from app.models.provider_dispute_intelligence import DisputeEvidenceComparisonModel,DisputeRAGItemModel,DisputeRAGRunModel,DisputeReviewCheckpointModel
from app.models.provider_dispute_resolution import *
from app.models.recovery_operations import ProviderDisputeModel,RecoveryCorrespondenceModel,RecoveryOutcomeModel,RecoveryTaskModel
from app.repositories.provider_dispute_intelligence import ProviderDisputeIntelligenceRepository
from app.repositories.provider_dispute_resolution import ProviderDisputeResolutionRepository
from app.repositories.recovery_operations import RecoveryOperationsRepository
from app.repositories.tenancy import MembershipRepository
from app.realtime.events import enqueue_realtime_event
from app.services.review_workbench import ReviewConflictError,ReviewLockError
from app.services.recovery_operations import RecoveryOperationsService

def _now():return datetime.now(UTC)
def _canon(v):return json.dumps(v,sort_keys=True,separators=(",",":"),default=str)
def _sha(v):return hashlib.sha256((v if isinstance(v,str) else _canon(v)).encode()).hexdigest()
def _money(v):return Decimal(str(v)).quantize(Decimal("0.01"))

class ProviderDisputeResolutionService:
    READ_ROLES={"finance_operator","finance_analyst","finance_approver","accounting_controller","auditor","tenant_admin"}
    def __init__(self,session:Session,tenant_id:str):
        self.session=session;self.tenant_id=tenant_id;self.repo=ProviderDisputeResolutionRepository(session,tenant_id);self.intel=ProviderDisputeIntelligenceRepository(session,tenant_id);self.recovery=RecoveryOperationsRepository(session,tenant_id);self.members=MembershipRepository(session,tenant_id)
    def _member(self,user_id):
        m=self.members.get_by_user(user_id)
        if m is None or m.status!="active":raise ReviewConflictError("active human tenant membership required")
        return m
    def _reader(self,user_id):
        m=self._member(user_id)
        if m.role not in self.READ_ROLES:raise ReviewConflictError("provider dispute resolution read membership required")
        return m
    def _investigator(self,user_id):
        m=self._member(user_id)
        if m.role not in {"finance_operator","finance_analyst"}:raise ReviewConflictError("human finance investigator required")
        return m
    def _approver(self,user_id):
        m=self._member(user_id)
        if m.role!="finance_approver":raise ReviewConflictError("independent human finance approver required")
        return m
    def _case_dispute(self,case_id,dispute_id,for_update=False):
        c=self.recovery.case(case_id,for_update)
        if c is None:raise LookupError("recovery case not found")
        q=select(ProviderDisputeModel).where(ProviderDisputeModel.tenant_id==self.tenant_id,ProviderDisputeModel.dispute_id==dispute_id,ProviderDisputeModel.recovery_case_id==case_id)
        if for_update:q=q.with_for_update()
        d=self.session.scalar(q)
        if d is None:raise LookupError("provider dispute not found")
        return c,d
    def _emit(self,c,d,event_type,payload,trace_id=None):
        enqueue_realtime_event(self.session,envelope=EventEnvelope(event_id=f"pdr_{uuid4().hex}",event_type=event_type,tenant_id=self.tenant_id,claim_id=c.claim_id,aggregate_type="provider_dispute_resolution",aggregate_id=d.dispute_id,occurred_at=_now(),trace_id=trace_id,producer="medclaimiq-provider-dispute-resolution",payload=payload,metadata={"recovery_case_id":c.recovery_case_id,"dispute_id":d.dispute_id,"status":payload.get("status",d.status)}),topic=EventTopic.CLAIMS.value)
    def _audit(self,c,d,packet_id,event_type,actor_id,payload,key,trace_id=None):
        existing=self.session.scalar(select(ProviderDisputeResolutionAuditEventModel).where(ProviderDisputeResolutionAuditEventModel.tenant_id==self.tenant_id,ProviderDisputeResolutionAuditEventModel.idempotency_key==key))
        if existing:return existing
        prior=self.repo.audit(d.dispute_id);seq=self.repo.next_audit_sequence(d.dispute_id);prev=prior[-1].event_sha256 if prior else None;now=_now();safe=json.loads(_canon(payload));digest=_sha({"case":c.recovery_case_id,"dispute":d.dispute_id,"packet":packet_id,"sequence":seq,"event":event_type,"actor":actor_id,"payload":safe,"previous":prev,"at":now})
        return self.repo.add(ProviderDisputeResolutionAuditEventModel(audit_event_id=f"pdraud_{uuid4().hex}",tenant_id=self.tenant_id,recovery_case_id=c.recovery_case_id,dispute_id=d.dispute_id,packet_id=packet_id,sequence=seq,event_type=event_type,actor_type="human_finance_approver",actor_id=actor_id,payload=safe,previous_event_sha256=prev,event_sha256=digest,idempotency_key=key,trace_id=trace_id,occurred_at=now))
    def _latest_recommendation(self,dispute_id):
        rows=self.intel.recommendation_runs(dispute_id);return rows[-1] if rows else None
    @staticmethod
    def _recommendation_matches(recommendation,outcome):
        return {"uphold_recovery":"uphold_recovery","consider_reduce_recovery":"reduce_recovery","consider_withdraw_recovery":"withdraw_recovery"}.get(recommendation)==outcome
    def _normalize_target(self,c,outcome,amount):
        original=_money(c.target_recovery_amount);value=_money(amount)
        if outcome=="uphold_recovery":
            if value!=original:raise ReviewConflictError("uphold recovery must preserve the governed recovery target")
        elif outcome=="withdraw_recovery":
            if value!=Decimal("0.00"):raise ReviewConflictError("withdraw recovery must set target to zero")
        elif outcome=="reduce_recovery":
            if not (Decimal("0.00")<=value<original):raise ReviewConflictError("reduced recovery target must be below the current governed target")
        else:raise ValueError("unsupported final provider dispute outcome")
        return original,value
    def _validation(self,d,packet):
        snap=self.intel.latest_snapshot(d.dispute_id);blockers=[]
        if snap is None or snap.status!="locked" or snap.snapshot_id!=packet.snapshot_id or snap.snapshot_sha256!=packet.snapshot_sha256:blockers.append("locked_dispute_snapshot_required_or_changed")
        comparisons=[] if snap is None else [x for x in self.intel.comparisons(d.dispute_id) if x.snapshot_id==snap.snapshot_id]
        material=[x.comparison_id for x in comparisons if x.severity=="material" and x.comparison_type in {"contradictory","changed"}]
        policy=[x.comparison_id for x in comparisons if x.severity=="material" and x.field=="payment_policy"]
        unresolved=sorted(set(material)-set(packet.resolved_comparison_refs));unresolved_policy=sorted(set(policy)-set(packet.resolved_comparison_refs))
        if unresolved:blockers.append("unresolved_material_evidence_conflicts")
        if unresolved_policy:blockers.append("unresolved_material_policy_conflicts")
        open_missing=[x.request_id for x in self.intel.missing_requests(d.dispute_id) if x.status=="open"]
        if open_missing:blockers.append("open_missing_evidence_requests")
        if not packet.citation_refs:blockers.append("citations_required")
        if not packet.reason_codes:blockers.append("reason_codes_required")
        if len((packet.rationale or "").strip())<20:blockers.append("human_rationale_required")
        rag_ids=set()
        if snap is not None:
            run_ids=list(self.session.scalars(select(DisputeRAGRunModel.run_id).where(DisputeRAGRunModel.tenant_id==self.tenant_id,DisputeRAGRunModel.dispute_id==d.dispute_id,DisputeRAGRunModel.snapshot_id==snap.snapshot_id)))
            if run_ids:rag_ids=set(self.session.scalars(select(DisputeRAGItemModel.item_id).where(DisputeRAGItemModel.tenant_id==self.tenant_id,DisputeRAGItemModel.run_id.in_(run_ids))))
        valid=rag_ids|{x.comparison_id for x in comparisons};invalid=sorted(set(packet.citation_refs)-valid)
        if invalid:blockers.append("invalid_citation_refs")
        cps={x.checkpoint_id for x in self.intel.checkpoints(d.dispute_id)};invalid_cp=sorted(set(packet.checkpoint_refs)-cps)
        if invalid_cp:blockers.append("invalid_checkpoint_refs")
        if packet.recommendation_disagreement and not (packet.recommendation_disagreement_reason or "").strip():blockers.append("recommendation_disagreement_reason_required")
        details={"snapshot_locked":snap is not None and snap.status=="locked","citation_count":len(packet.citation_refs),"invalid_citation_refs":invalid,"invalid_checkpoint_refs":invalid_cp,"material_conflicts":material,"unresolved_material_conflicts":unresolved,"unresolved_policy_conflicts":unresolved_policy,"open_missing_evidence_requests":open_missing,"reason_code_count":len(packet.reason_codes),"recommendation_disagreement":packet.recommendation_disagreement}
        return details,list(dict.fromkeys(blockers))
    def save_packet(self,case_id,dispute_id,user_id,*,outcome,amended_target_amount,rationale,reason_codes,citation_refs,resolved_comparison_refs,checkpoint_refs,recommendation_disagreement_reason,expected_case_version,expected_packet_version,idempotency_key,trace_id=None):
        self._approver(user_id);existing=self.session.scalar(select(ProviderDisputeDecisionPacketModel).where(ProviderDisputeDecisionPacketModel.tenant_id==self.tenant_id,ProviderDisputeDecisionPacketModel.idempotency_key==idempotency_key))
        if existing:return existing
        c,d=self._case_dispute(case_id,dispute_id,True)
        if d.status=="resolved" or self.repo.final(dispute_id):raise ReviewConflictError("provider dispute already has a final governed resolution")
        if c.case_version!=expected_case_version:raise ReviewConflictError("stale recovery case version")
        if d.submitted_by_user_id==user_id or c.assigned_investigator_user_id==user_id:raise ReviewConflictError("primary dispute resolver must be independent of provider submitter and recovery investigator")
        if outcome not in FINAL_OUTCOMES:raise ValueError("unsupported final provider dispute outcome")
        original,amended=self._normalize_target(c,outcome,amended_target_amount);delta=amended-original
        latest=self.repo.latest_packet(dispute_id);next_version=1 if latest is None else latest.packet_version+1
        if expected_packet_version is not None and (latest is None or latest.packet_version!=expected_packet_version):raise ReviewConflictError("stale provider dispute packet version")
        snap=self.intel.latest_snapshot(dispute_id)
        if snap is None or snap.status!="locked":raise ReviewConflictError("locked Release 45 dispute evidence snapshot required")
        rec=self._latest_recommendation(dispute_id);disagreement=bool(rec and not self._recommendation_matches(rec.recommendation,outcome));pct=0 if original<=0 else abs(delta/original*100);material_change=abs(delta)>=Decimal(str(MATERIAL_FINANCIAL_CHANGE_ABS)) or pct>=Decimal(str(MATERIAL_FINANCIAL_CHANGE_PCT));dual=bool(d.material or material_change)
        now=_now();row=self.repo.add(ProviderDisputeDecisionPacketModel(packet_id=f"pdrpkt_{uuid4().hex}",tenant_id=self.tenant_id,recovery_case_id=case_id,dispute_id=dispute_id,claim_id=c.claim_id,primary_resolver_user_id=user_id,second_resolver_user_id=None,snapshot_id=snap.snapshot_id,snapshot_sha256=snap.snapshot_sha256,recommendation_run_id=None if rec is None else rec.recommendation_run_id,outcome=outcome,rationale=rationale,reason_codes=reason_codes,citation_refs=citation_refs,resolved_comparison_refs=resolved_comparison_refs,checkpoint_refs=checkpoint_refs,original_target_amount=original,amended_target_amount=amended,financial_delta=delta,material_target_change=material_change,recommendation_disagreement=disagreement,recommendation_disagreement_reason=recommendation_disagreement_reason,completeness={},blocker_codes=[],dual_control_required=dual,status="draft",packet_version=next_version,expected_case_version=expected_case_version,locked_payload_sha256=None,final_resolution_id=None,idempotency_key=idempotency_key,trace_id=trace_id,created_at=now,updated_at=now,locked_at=None,closed_at=None))
        details,blockers=self._validation(d,row);row.completeness=details;row.blocker_codes=blockers;self._audit(c,d,row.packet_id,"provider_dispute_resolution.packet.created",user_id,{"outcome":outcome,"amended_target_amount":str(amended),"dual_control_required":dual,"blockers":blockers},f"audit:{idempotency_key}",trace_id);self._emit(c,d,"provider_dispute_resolution.packet.created",{"packet_id":row.packet_id,"status":row.status,"dual_control_required":dual},trace_id);return row
    def lock_packet(self,case_id,dispute_id,packet_id,user_id,*,expected_packet_version,idempotency_key,trace_id=None):
        self._approver(user_id);c,d=self._case_dispute(case_id,dispute_id,True);p=self.repo.packet(packet_id,for_update=True)
        if p is None or p.dispute_id!=dispute_id:raise LookupError("provider dispute decision packet not found")
        if p.primary_resolver_user_id!=user_id:raise ReviewConflictError("only the primary independent human resolver may lock this packet")
        if p.packet_version!=expected_packet_version:raise ReviewConflictError("stale provider dispute packet version")
        if c.case_version!=p.expected_case_version:raise ReviewConflictError("recovery case changed after packet preparation")
        details,blockers=self._validation(d,p);p.completeness=details;p.blocker_codes=blockers
        if blockers:raise ReviewConflictError("provider dispute packet blocked: "+",".join(blockers))
        payload={"packet_id":p.packet_id,"snapshot_sha256":p.snapshot_sha256,"outcome":p.outcome,"rationale":p.rationale,"reason_codes":p.reason_codes,"citations":p.citation_refs,"resolved_comparisons":p.resolved_comparison_refs,"checkpoints":p.checkpoint_refs,"original_target":str(p.original_target_amount),"amended_target":str(p.amended_target_amount),"financial_delta":str(p.financial_delta),"recommendation_run_id":p.recommendation_run_id,"recommendation_disagreement":p.recommendation_disagreement,"recommendation_disagreement_reason":p.recommendation_disagreement_reason,"dual_control_required":p.dual_control_required,"packet_version":p.packet_version}
        p.locked_payload_sha256=_sha(payload);p.status="pending_second_review" if p.dual_control_required else "locked";p.locked_at=_now();p.updated_at=p.locked_at;self._audit(c,d,p.packet_id,"provider_dispute_resolution.packet.locked",user_id,{"locked_payload_sha256":p.locked_payload_sha256,"status":p.status},f"audit:{idempotency_key}",trace_id);self._emit(c,d,"provider_dispute_resolution.packet.locked",{"packet_id":p.packet_id,"status":p.status,"dual_control_required":p.dual_control_required},trace_id);return p
    def second_review(self,case_id,dispute_id,packet_id,user_id,*,action,rationale,expected_packet_version,idempotency_key,trace_id=None):
        self._approver(user_id);c,d=self._case_dispute(case_id,dispute_id,True);p=self.repo.packet(packet_id,for_update=True)
        if p is None or p.dispute_id!=dispute_id:raise LookupError("provider dispute decision packet not found")
        if not p.dual_control_required:raise ReviewConflictError("second review is not required")
        if p.status not in {"pending_second_review","second_review_rejected"}:raise ReviewConflictError("packet is not awaiting second review")
        if p.packet_version!=expected_packet_version:raise ReviewConflictError("stale provider dispute packet version")
        if action not in SECOND_REVIEW_ACTIONS:raise ValueError("unsupported second review action")
        if user_id in {p.primary_resolver_user_id,d.submitted_by_user_id,c.assigned_investigator_user_id}:raise ReviewConflictError("independent second human finance approver required")
        existing=self.session.scalar(select(ProviderDisputeSecondReviewModel).where(ProviderDisputeSecondReviewModel.tenant_id==self.tenant_id,ProviderDisputeSecondReviewModel.packet_id==packet_id,ProviderDisputeSecondReviewModel.reviewer_user_id==user_id))
        if existing:return p
        digest=_sha({"packet":p.locked_payload_sha256,"reviewer":user_id,"action":action,"rationale":rationale,"packet_version":p.packet_version});self.repo.add(ProviderDisputeSecondReviewModel(second_review_id=f"pdr2_{uuid4().hex}",tenant_id=self.tenant_id,recovery_case_id=case_id,dispute_id=dispute_id,packet_id=packet_id,reviewer_user_id=user_id,action=action,rationale=rationale,packet_version=p.packet_version,payload_sha256=digest,created_at=_now()));p.second_resolver_user_id=user_id;p.status="second_approved" if action=="approve" else "second_review_rejected";p.updated_at=_now();self._audit(c,d,p.packet_id,"provider_dispute_resolution.second_review.completed",user_id,{"action":action,"status":p.status},f"audit:{idempotency_key}",trace_id);self._emit(c,d,"provider_dispute_resolution.second_review.completed",{"packet_id":p.packet_id,"status":p.status,"action":action},trace_id);return p
    def _append_position(self,c,d,p,user_id):
        rows=self.repo.positions(c.recovery_case_id)
        if not rows:
            baseline_payload={"case":c.recovery_case_id,"sequence":1,"target":str(p.original_target_amount),"currency":c.currency,"source":"release44_recovery_position"};base=self.repo.add(RecoveryPositionVersionModel(position_version_id=f"recpos_{uuid4().hex}",tenant_id=self.tenant_id,recovery_case_id=c.recovery_case_id,dispute_id=None,sequence=1,target_recovery_amount=p.original_target_amount,currency=c.currency,source_type="release44_recovery_position",source_id=c.recovery_case_id,supersedes_position_version_id=None,previous_payload_sha256=None,payload_sha256=_sha(baseline_payload),created_by_user_id=user_id,effective_at=_now()));rows=[base]
        prev=rows[-1];seq=prev.sequence+1;payload={"case":c.recovery_case_id,"dispute":d.dispute_id,"sequence":seq,"target":str(p.amended_target_amount),"currency":c.currency,"source":"provider_dispute_final_resolution","previous":prev.payload_sha256};return self.repo.add(RecoveryPositionVersionModel(position_version_id=f"recpos_{uuid4().hex}",tenant_id=self.tenant_id,recovery_case_id=c.recovery_case_id,dispute_id=d.dispute_id,sequence=seq,target_recovery_amount=p.amended_target_amount,currency=c.currency,source_type="provider_dispute_final_resolution",source_id=p.packet_id,supersedes_position_version_id=prev.position_version_id,previous_payload_sha256=prev.payload_sha256,payload_sha256=_sha(payload),created_by_user_id=user_id,effective_at=_now()))
    def close(self,case_id,dispute_id,packet_id,user_id,*,expected_packet_version,expected_case_version,idempotency_key,trace_id=None):
        self._approver(user_id);existing=self.repo.final(dispute_id)
        if existing:return existing
        c,d=self._case_dispute(case_id,dispute_id,True);p=self.repo.packet(packet_id,for_update=True)
        if p is None or p.dispute_id!=dispute_id:raise LookupError("provider dispute decision packet not found")
        if p.primary_resolver_user_id!=user_id:raise ReviewConflictError("only the primary independent human resolver may close the dispute")
        if p.packet_version!=expected_packet_version or c.case_version!=expected_case_version or c.case_version!=p.expected_case_version:raise ReviewConflictError("stale recovery case or dispute packet version")
        if not p.locked_payload_sha256:raise ReviewConflictError("locked dispute packet required")
        if p.dual_control_required and p.status!="second_approved":raise ReviewConflictError("independent second human finance approval required")
        if not p.dual_control_required and p.status!="locked":raise ReviewConflictError("locked dispute packet required")
        details,blockers=self._validation(d,p)
        if blockers:raise ReviewConflictError("provider dispute final closure blocked: "+",".join(blockers))
        now=_now();position=self._append_position(c,d,p,user_id);payload={"case":case_id,"dispute":dispute_id,"packet":packet_id,"outcome":p.outcome,"original_target":str(p.original_target_amount),"amended_target":str(p.amended_target_amount),"snapshot_sha256":p.snapshot_sha256,"locked_packet_sha256":p.locked_payload_sha256,"position_sha256":position.payload_sha256,"primary":user_id,"second":p.second_resolver_user_id};resolution=self.repo.add(ProviderDisputeFinalResolutionModel(resolution_id=f"pdrfinal_{uuid4().hex}",tenant_id=self.tenant_id,recovery_case_id=case_id,dispute_id=dispute_id,packet_id=packet_id,primary_resolver_user_id=user_id,second_resolver_user_id=p.second_resolver_user_id,outcome=p.outcome,original_target_amount=p.original_target_amount,amended_target_amount=p.amended_target_amount,financial_delta=p.financial_delta,snapshot_sha256=p.snapshot_sha256,packet_locked_sha256=p.locked_payload_sha256,position_version_id=position.position_version_id,correspondence_id=None,reversal_referral_id=None,provenance={"validation":details,"recommendation_run_id":p.recommendation_run_id,"citations":p.citation_refs,"resolved_comparisons":p.resolved_comparison_refs,"checkpoint_refs":p.checkpoint_refs},payload_sha256=_sha(payload),idempotency_key=idempotency_key,trace_id=trace_id,resolved_at=now))
        reduction=max(Decimal("0.00"),_money(p.original_target_amount)-_money(p.amended_target_amount))
        if reduction>0:
            rtype="recoupment_reversal_referral" if "recoup" in c.referral_type else "adjustment_reversal_referral" if "adjust" in c.referral_type else "reconciliation_review_referral";refpayload={"resolution":resolution.resolution_id,"type":rtype,"amount":str(reduction),"currency":c.currency,"destination":"release41_accounting_human_review"};ref=self.repo.add(RecoveryAmendmentReferralModel(reversal_referral_id=f"recamend_{uuid4().hex}",tenant_id=self.tenant_id,recovery_case_id=case_id,dispute_id=dispute_id,resolution_id=resolution.resolution_id,referral_type=rtype,destination="release41_accounting_human_review",amount=reduction,currency=c.currency,reason_code="provider_dispute_recovery_amendment",status="pending_human_finance_action",external_reference=None,verified_by_user_id=None,verified_at=None,payload_sha256=_sha(refpayload),created_by_user_id=user_id,created_at=now));resolution.reversal_referral_id=ref.reversal_referral_id
        corr_body=f"Provider dispute {d.external_reference} was resolved by authorized human finance review. Outcome: {p.outcome}. Governed recovery target: {p.amended_target_amount} {c.currency}. Any accounting reversal or payment effect remains subject to separate governed finance controls.";corr=self.recovery.add(RecoveryCorrespondenceModel(correspondence_id=f"reccorr_{uuid4().hex}",tenant_id=self.tenant_id,recovery_case_id=case_id,dispute_id=dispute_id,direction="outbound",channel="portal",subject="Provider dispute resolution",body=corr_body,external_message_id=None,body_sha256=_sha(corr_body),actor_type="human_finance_approver",actor_id=user_id,idempotency_key=f"pdr-resolution:{resolution.resolution_id}",occurred_at=now));resolution.correspondence_id=corr.correspondence_id
        self.recovery.add(RecoveryOutcomeModel(outcome_id=f"recout_{uuid4().hex}",tenant_id=self.tenant_id,recovery_case_id=case_id,outcome_type="provider_dispute_recovery_amendment",source_type="provider_dispute_final_resolution",source_id=resolution.resolution_id,amount=p.amended_target_amount,currency=c.currency,status="human_resolved",external_reference=d.external_reference,details={"original_target":str(p.original_target_amount),"amended_target":str(p.amended_target_amount),"position_version_id":position.position_version_id,"reversal_referral_id":resolution.reversal_referral_id},payload_sha256=_sha({"resolution":resolution.resolution_id,"target":str(p.amended_target_amount),"position":position.payload_sha256}),idempotency_key=f"pdr-outcome:{resolution.resolution_id}",recorded_by_actor_type="human_finance_approver",recorded_by_actor_id=user_id,occurred_at=now))
        d.status="resolved";d.assigned_resolver_user_id=user_id;d.resolution_outcome=p.outcome;d.resolution_rationale=p.rationale;d.resolution_amount=p.amended_target_amount;d.resolved_at=now;c.target_recovery_amount=p.amended_target_amount;c.status="recovery_amended" if p.outcome!="uphold_recovery" else "dispute_resolved";c.case_version+=1;c.updated_at=now;p.final_resolution_id=resolution.resolution_id;p.status="closed";p.closed_at=now;p.updated_at=now
        for cp in self.intel.checkpoints(dispute_id):
            if cp.status=="waiting_human":cp.status="completed";cp.requires_human_action=False;cp.resumed_by_user_id=user_id;cp.resumed_at=now
        for t in self.recovery.tasks(case_id):
            if t.task_type in {"provider_dispute_review","material_dispute_resolution"} and t.status=="open":t.status="completed";t.completed_at=now
        self._audit(c,d,p.packet_id,"provider_dispute_resolution.closed",user_id,{"resolution_id":resolution.resolution_id,"outcome":p.outcome,"amended_target_amount":str(p.amended_target_amount),"position_version_id":position.position_version_id,"reversal_referral_id":resolution.reversal_referral_id,"correspondence_id":corr.correspondence_id},f"audit:{idempotency_key}",trace_id);self._emit(c,d,"provider_dispute_resolution.closed",{"resolution_id":resolution.resolution_id,"status":"resolved","outcome":p.outcome,"amended_target_amount":str(p.amended_target_amount)},trace_id);return resolution
    def _assert_recovery_lease(self,c,user_id,lease_token):
        lease=self.recovery.lease(c.recovery_case_id,True)
        if lease is None or lease.investigator_user_id!=user_id or lease.lease_token_sha256!=_sha(lease_token):raise ReviewLockError("valid recovery investigator lease required")
        now=_now();exp=lease.expires_at if lease.expires_at.tzinfo else lease.expires_at.replace(tzinfo=UTC)
        if exp<=now:raise ReviewLockError("recovery investigator lease expired")
    def verify_reconciliation_referral(self,case_id,dispute_id,referral_id,user_id,*,status,external_reference,expected_case_version,lease_token,idempotency_key,trace_id=None):
        self._investigator(user_id);c,d=self._case_dispute(case_id,dispute_id,True)
        if c.case_version!=expected_case_version:raise ReviewConflictError("stale recovery case version")
        self._assert_recovery_lease(c,user_id,lease_token)
        row=self.session.scalar(select(RecoveryAmendmentReferralModel).where(RecoveryAmendmentReferralModel.tenant_id==self.tenant_id,RecoveryAmendmentReferralModel.reversal_referral_id==referral_id,RecoveryAmendmentReferralModel.recovery_case_id==case_id,RecoveryAmendmentReferralModel.dispute_id==dispute_id).with_for_update())
        if row is None:raise LookupError("recovery amendment referral not found")
        if status not in {"verified","no_change_required","exception"}:raise ValueError("unsupported reconciliation verification status")
        if row.status in {"verified","no_change_required"}:return row
        row.status=status;row.external_reference=external_reference;row.verified_by_user_id=user_id;row.verified_at=_now();c.case_version+=1;c.updated_at=row.verified_at
        if status in {"verified","no_change_required"}:c.last_verified_at=row.verified_at;c.status="reconciliation_verified"
        details={"referral_id":referral_id,"referral_type":row.referral_type,"external_reference":external_reference,"verification_status":status,"amount":str(row.amount)}
        self.recovery.add(RecoveryOutcomeModel(outcome_id=f"recout_{uuid4().hex}",tenant_id=self.tenant_id,recovery_case_id=case_id,outcome_type="recovery_amendment_reconciliation_verification",source_type=row.referral_type,source_id=referral_id,amount=row.amount,currency=row.currency,status=status,external_reference=external_reference,details=details,payload_sha256=_sha(details),idempotency_key=idempotency_key,recorded_by_actor_type="human_finance_investigator",recorded_by_actor_id=user_id,occurred_at=row.verified_at))
        self._audit(c,d,None,"provider_dispute_resolution.reconciliation.verified",user_id,details,f"audit:{idempotency_key}",trace_id);self._emit(c,d,"provider_dispute_resolution.reconciliation.verified",{"referral_id":referral_id,"status":status},trace_id);return row
    def finalize_recovery_case(self,case_id,dispute_id,user_id,*,rationale,expected_case_version,lease_token,idempotency_key,trace_id=None):
        self._investigator(user_id);c,d=self._case_dispute(case_id,dispute_id,True)
        if c.case_version!=expected_case_version:raise ReviewConflictError("stale recovery case version")
        self._assert_recovery_lease(c,user_id,lease_token)
        if self.repo.final(dispute_id) is None or d.status!="resolved":raise ReviewConflictError("final human provider dispute resolution required before recovery closure")
        pending=[x.reversal_referral_id for x in self.repo.referrals(case_id) if x.dispute_id==dispute_id and x.status not in {"verified","no_change_required"}]
        if pending:raise ReviewConflictError("recovery closure blocked by unverified accounting/reconciliation amendment referrals")
        if c.last_verified_at is None:raise ReviewConflictError("verified recovery/accounting outcome required before final recovery closure")
        closed=RecoveryOperationsService(self.session,self.tenant_id).close_case(case_id,user_id,reason_code="provider_dispute_resolved",rationale=rationale,expected_case_version=expected_case_version,lease_token=lease_token,idempotency_key=idempotency_key)
        self._audit(closed,d,None,"provider_dispute_resolution.recovery.closed",user_id,{"reason":"provider_dispute_resolved","target_recovery_amount":str(closed.target_recovery_amount)},f"audit:p46-close:{idempotency_key}",trace_id);self._emit(closed,d,"provider_dispute_resolution.recovery.closed",{"status":"closed","target_recovery_amount":str(closed.target_recovery_amount)},trace_id);return closed
    def packet_view(self,p):return {"packet_id":p.packet_id,"dispute_id":p.dispute_id,"snapshot_id":p.snapshot_id,"snapshot_sha256":p.snapshot_sha256,"recommendation_run_id":p.recommendation_run_id,"outcome":p.outcome,"original_target_amount":str(p.original_target_amount),"amended_target_amount":str(p.amended_target_amount),"financial_delta":str(p.financial_delta),"material_target_change":p.material_target_change,"recommendation_disagreement":p.recommendation_disagreement,"completeness":p.completeness,"blocker_codes":p.blocker_codes,"dual_control_required":p.dual_control_required,"status":p.status,"packet_version":p.packet_version,"expected_case_version":p.expected_case_version,"locked_payload_sha256":p.locked_payload_sha256,"primary_resolver_user_id":p.primary_resolver_user_id,"second_resolver_user_id":p.second_resolver_user_id,"final_resolution_id":p.final_resolution_id}
    def snapshot(self,case_id,dispute_id,user_id):
        self._reader(user_id);c,d=self._case_dispute(case_id,dispute_id);p=self.repo.latest_packet(dispute_id);final=self.repo.final(dispute_id);positions=self.repo.positions(case_id);refs=self.repo.referrals(case_id);return {"recovery_case_id":case_id,"dispute_id":dispute_id,"dispute_status":d.status,"recovery_case_version":c.case_version,"current_target_recovery_amount":str(c.target_recovery_amount),"packet":None if p is None else self.packet_view(p),"final_resolution":None if final is None else {"resolution_id":final.resolution_id,"outcome":final.outcome,"original_target_amount":str(final.original_target_amount),"amended_target_amount":str(final.amended_target_amount),"financial_delta":str(final.financial_delta),"snapshot_sha256":final.snapshot_sha256,"packet_locked_sha256":final.packet_locked_sha256,"position_version_id":final.position_version_id,"correspondence_id":final.correspondence_id,"reversal_referral_id":final.reversal_referral_id,"payload_sha256":final.payload_sha256,"resolved_at":final.resolved_at},"position_versions":[{"position_version_id":x.position_version_id,"sequence":x.sequence,"target_recovery_amount":str(x.target_recovery_amount),"source_type":x.source_type,"source_id":x.source_id,"supersedes_position_version_id":x.supersedes_position_version_id,"previous_payload_sha256":x.previous_payload_sha256,"payload_sha256":x.payload_sha256,"effective_at":x.effective_at} for x in positions],"reversal_referrals":[{"reversal_referral_id":x.reversal_referral_id,"referral_type":x.referral_type,"destination":x.destination,"amount":str(x.amount),"currency":x.currency,"status":x.status,"external_reference":x.external_reference,"verified_by_user_id":x.verified_by_user_id,"verified_at":x.verified_at,"payload_sha256":x.payload_sha256} for x in refs],"audit_chain":[{"sequence":x.sequence,"event_type":x.event_type,"actor_id":x.actor_id,"previous_event_sha256":x.previous_event_sha256,"event_sha256":x.event_sha256,"occurred_at":x.occurred_at} for x in self.repo.audit(dispute_id)],"authority":{"ai_resolves_dispute":False,"automation_changes_accounting":False,"automation_authorizes_payment":False,"automation_collects_or_moves_funds":False,"final_resolution":"authorized_human_finance_approver_only"}}
    def traceability(self,case_id,dispute_id,user_id):
        s=self.snapshot(case_id,dispute_id,user_id);intel_snapshot=self.intel.latest_snapshot(dispute_id);return {"recovery_case_id":case_id,"dispute_id":dispute_id,"release45_snapshot":None if intel_snapshot is None else {"snapshot_id":intel_snapshot.snapshot_id,"snapshot_sha256":intel_snapshot.snapshot_sha256},"decision_packet":s["packet"],"final_resolution":s["final_resolution"],"recovery_position_supersession":s["position_versions"],"accounting_reconciliation_referrals":s["reversal_referrals"],"authority":s["authority"]}
