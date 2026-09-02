from __future__ import annotations
from decimal import Decimal
import pytest
from sqlalchemy import select
from app.domain.appeal_resolution import AppealFinalOutcome, AppealSecondReviewAction
from app.domain.claims import HumanDecision
from app.models.appeal_reconsideration import AppealMissingEvidenceRequestModel
from app.models.post_decision import DecisionNoticeModel
from app.services.appeal_reconsideration import AppealReconsiderationService
from app.services.appeal_resolution import AppealResolutionService
from app.services.post_decision import PostDecisionService
from app.services.review_workbench import ReviewConflictError
from tests.test_appeal_evidence_reconsideration import factory, close_and_appeal


def prepare(db):
    appeal=close_and_appeal(db); r=AppealReconsiderationService(db,"tenant-a")
    snapshot=r.build_snapshot("claim-1",appeal.appeal_id,"reviewer-3")
    search=r.search("claim-1",appeal.appeal_id,"invoice amount CPT 99213",limit=8)
    agent=r.run_reconsideration_agent("claim-1",appeal.appeal_id,idempotency_key="release39-agent")
    material=[x.comparison_id for x in r.repo.comparisons(appeal.appeal_id,snapshot.snapshot_id) if x.severity=="material"]
    citations=[x.item_id for x in search["items"]]
    return appeal,snapshot,agent,material,citations


def test_material_financial_change_requires_dual_control_and_closes_with_supersession_notice():
    f=factory()
    with f() as db:
        appeal,snapshot,agent,material,citations=prepare(db); svc=AppealResolutionService(db,"tenant-a")
        packet=svc.save_packet("claim-1",appeal.appeal_id,"reviewer-3",outcome=AppealFinalOutcome.MODIFY,controlling_decision=HumanDecision.PARTIAL_APPROVE,rationale="Independent human review finds the supplemental evidence supports a reduced covered amount.",reason_codes=["evidence_contradicts","human_judgment"],citation_refs=citations,resolved_comparison_refs=material,annotation_refs=[],checkpoint_refs=[],reconsidered_approved_amount=Decimal("700.00"),recommendation_disagreement_reason=None,expected_appeal_version=appeal.appeal_version,expected_packet_version=None,idempotency_key="release39-packet")
        assert packet.dual_control_required and packet.material_financial_change and packet.financial_delta==Decimal("-300.00")
        packet=svc.lock_packet("claim-1",appeal.appeal_id,packet.packet_id,"reviewer-3",expected_packet_version=1,idempotency_key="release39-lock")
        assert packet.status=="pending_second_review" and packet.locked_payload_sha256
        with pytest.raises(ReviewConflictError): svc.close("claim-1",appeal.appeal_id,packet.packet_id,"reviewer-3",expected_packet_version=1,expected_appeal_version=appeal.appeal_version,idempotency_key="release39-too-early")
        packet=svc.second_review("claim-1",appeal.appeal_id,packet.packet_id,"reviewer-2",action=AppealSecondReviewAction.APPROVE,rationale="Second independent human reviewer confirms the evidence-bound material financial change.",expected_packet_version=1,idempotency_key="release39-second")
        assert packet.status=="second_review_approved" and packet.second_reviewer_user_id=="reviewer-2"
        final=svc.close("claim-1",appeal.appeal_id,packet.packet_id,"reviewer-3",expected_packet_version=1,expected_appeal_version=appeal.appeal_version,idempotency_key="release39-close")
        assert final.controlling_decision=="partial_approve" and final.history_version_id and final.notice_id
        history=svc.post.history("claim-1"); assert history[-1].source_type=="appeal_final_resolution" and history[-1].previous_version_sha256
        notice=db.get(DecisionNoticeModel,final.notice_id); assert notice.status=="draft" and notice.evidence_snapshot_sha256==snapshot.snapshot_sha256
        released=PostDecisionService(db,"tenant-a").release_notice("claim-1",notice.notice_id,"reviewer-3",idempotency_key="release39-release")
        assert released.status=="delivery_pending" and released.resolution_id==final.resolution_id
        snap=svc.snapshot("claim-1",appeal.appeal_id); assert snap["final_resolution"]["resolution_id"]==final.resolution_id and snap["authority"]["llm"] is False


def test_unresolved_material_contradiction_blocks_lock():
    f=factory()
    with f() as db:
        appeal,_,_,material,citations=prepare(db);svc=AppealResolutionService(db,"tenant-a")
        p=svc.save_packet("claim-1",appeal.appeal_id,"reviewer-3",outcome=AppealFinalOutcome.MODIFY,controlling_decision=HumanDecision.PARTIAL_APPROVE,rationale="Human reviewer proposes a changed amount but has not yet resolved all material contradictions.",reason_codes=["evidence_contradicts"],citation_refs=citations,resolved_comparison_refs=[],annotation_refs=[],checkpoint_refs=[],reconsidered_approved_amount=Decimal("700.00"),recommendation_disagreement_reason=None,expected_appeal_version=appeal.appeal_version,expected_packet_version=None,idempotency_key="release39-blocked")
        assert "unresolved_material_contradictions" in p.blocker_codes
        with pytest.raises(ReviewConflictError): svc.lock_packet("claim-1",appeal.appeal_id,p.packet_id,"reviewer-3",expected_packet_version=1,idempotency_key="release39-lock-blocked")


def test_open_missing_evidence_blocks_final_packet_lock():
    f=factory()
    with f() as db:
        appeal,_,_,material,citations=prepare(db);r=AppealReconsiderationService(db,"tenant-a");r.request_missing_evidence("claim-1",appeal.appeal_id,"reviewer-3",document_types=["provider_statement"],rationale="A provider statement is required before final reconsideration can be safely closed.",idempotency_key="release39-missing")
        svc=AppealResolutionService(db,"tenant-a");p=svc.save_packet("claim-1",appeal.appeal_id,"reviewer-3",outcome=AppealFinalOutcome.MODIFY,controlling_decision=HumanDecision.PARTIAL_APPROVE,rationale="Human reviewer has a provisional changed amount pending required evidence.",reason_codes=["missing_documents"],citation_refs=citations,resolved_comparison_refs=material,annotation_refs=[],checkpoint_refs=[],reconsidered_approved_amount=Decimal("700.00"),recommendation_disagreement_reason=None,expected_appeal_version=appeal.appeal_version,expected_packet_version=None,idempotency_key="release39-missing-packet")
        assert "open_missing_evidence_requests" in p.blocker_codes


def test_recommendation_disagreement_requires_human_reason():
    f=factory()
    with f() as db:
        appeal,_,_,material,citations=prepare(db);svc=AppealResolutionService(db,"tenant-a")
        with pytest.raises(ReviewConflictError):
            svc.save_packet("claim-1",appeal.appeal_id,"reviewer-3",outcome=AppealFinalOutcome.AFFIRM,controlling_decision=HumanDecision.APPROVE,rationale="The human reviewer chooses to affirm despite the recommendation after considering the full record.",reason_codes=["human_judgment"],citation_refs=citations,resolved_comparison_refs=material,annotation_refs=[],checkpoint_refs=[],reconsidered_approved_amount=Decimal("1000.00"),recommendation_disagreement_reason=None,expected_appeal_version=appeal.appeal_version,expected_packet_version=None,idempotency_key="release39-disagree")


def test_second_level_reviewer_independence_excludes_original_and_primary():
    f=factory()
    with f() as db:
        appeal,_,_,material,citations=prepare(db);svc=AppealResolutionService(db,"tenant-a")
        p=svc.save_packet("claim-1",appeal.appeal_id,"reviewer-3",outcome=AppealFinalOutcome.MODIFY,controlling_decision=HumanDecision.PARTIAL_APPROVE,rationale="Independent human reviewer proposes a material evidence-bound amount modification.",reason_codes=["evidence_contradicts"],citation_refs=citations,resolved_comparison_refs=material,annotation_refs=[],checkpoint_refs=[],reconsidered_approved_amount=Decimal("700.00"),recommendation_disagreement_reason=None,expected_appeal_version=appeal.appeal_version,expected_packet_version=None,idempotency_key="release39-independence")
        p=svc.lock_packet("claim-1",appeal.appeal_id,p.packet_id,"reviewer-3",expected_packet_version=1,idempotency_key="release39-ind-lock")
        for reviewer in ("reviewer-3","reviewer-1"):
            with pytest.raises(ReviewConflictError): svc.second_review("claim-1",appeal.appeal_id,p.packet_id,reviewer,action=AppealSecondReviewAction.APPROVE,rationale="This reviewer is deliberately disallowed by the independence rules.",expected_packet_version=1,idempotency_key=f"release39-bad-{reviewer}")

def test_optimistic_concurrency_blocks_stale_packet_and_appeal_versions():
    f=factory()
    with f() as db:
        appeal,_,_,material,citations=prepare(db);svc=AppealResolutionService(db,"tenant-a")
        p=svc.save_packet("claim-1",appeal.appeal_id,"reviewer-3",outcome=AppealFinalOutcome.MODIFY,controlling_decision=HumanDecision.PARTIAL_APPROVE,rationale="Independent reviewer records a material evidence-bound amount change for governed review.",reason_codes=["evidence_contradicts"],citation_refs=citations,resolved_comparison_refs=material,annotation_refs=[],checkpoint_refs=[],reconsidered_approved_amount=Decimal("700.00"),recommendation_disagreement_reason=None,expected_appeal_version=appeal.appeal_version,expected_packet_version=None,idempotency_key="release39-concurrency")
        with pytest.raises(ReviewConflictError,match="packet version conflict"):
            svc.lock_packet("claim-1",appeal.appeal_id,p.packet_id,"reviewer-3",expected_packet_version=99,idempotency_key="release39-stale-packet")
        p=svc.lock_packet("claim-1",appeal.appeal_id,p.packet_id,"reviewer-3",expected_packet_version=1,idempotency_key="release39-good-packet")
        p=svc.second_review("claim-1",appeal.appeal_id,p.packet_id,"reviewer-2",action=AppealSecondReviewAction.APPROVE,rationale="Second independent reviewer confirms the locked packet and material amount reconciliation.",expected_packet_version=1,idempotency_key="release39-concurrency-second")
        with pytest.raises(ReviewConflictError,match="appeal version conflict"):
            svc.close("claim-1",appeal.appeal_id,p.packet_id,"reviewer-3",expected_packet_version=1,expected_appeal_version=99,idempotency_key="release39-stale-appeal")


def test_invalid_traceability_references_and_missing_reason_codes_fail_closed():
    f=factory()
    with f() as db:
        appeal,_,_,material,citations=prepare(db);svc=AppealResolutionService(db,"tenant-a")
        with pytest.raises(ReviewConflictError,match="reason code"):
            svc.save_packet("claim-1",appeal.appeal_id,"reviewer-3",outcome=AppealFinalOutcome.MODIFY,controlling_decision=HumanDecision.PARTIAL_APPROVE,rationale="Independent human reviewer proposes an evidence-bound financial modification.",reason_codes=[],citation_refs=citations,resolved_comparison_refs=material,annotation_refs=[],checkpoint_refs=[],reconsidered_approved_amount=Decimal("700.00"),recommendation_disagreement_reason=None,expected_appeal_version=appeal.appeal_version,expected_packet_version=None,idempotency_key="release39-no-reasons")
        p=svc.save_packet("claim-1",appeal.appeal_id,"reviewer-3",outcome=AppealFinalOutcome.MODIFY,controlling_decision=HumanDecision.PARTIAL_APPROVE,rationale="Independent human reviewer proposes an evidence-bound financial modification.",reason_codes=["human_judgment"],citation_refs=[*citations,"unknown-citation"],resolved_comparison_refs=material,annotation_refs=["unknown-annotation"],checkpoint_refs=["unknown-checkpoint"],reconsidered_approved_amount=Decimal("700.00"),recommendation_disagreement_reason=None,expected_appeal_version=appeal.appeal_version,expected_packet_version=None,idempotency_key="release39-bad-refs")
        assert {"invalid_citation_refs","invalid_annotation_refs","invalid_checkpoint_refs"} <= set(p.blocker_codes)
        with pytest.raises(ReviewConflictError): svc.lock_packet("claim-1",appeal.appeal_id,p.packet_id,"reviewer-3",expected_packet_version=1,idempotency_key="release39-bad-refs-lock")
