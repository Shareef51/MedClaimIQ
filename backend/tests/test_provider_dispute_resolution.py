from __future__ import annotations
from decimal import Decimal
from pathlib import Path
import pytest
from app.services.provider_dispute_resolution import ProviderDisputeResolutionService
from app.services.review_workbench import ReviewConflictError
from tests.test_appeal_evidence_reconsideration import factory
from tests.test_provider_dispute_intelligence import seed_dispute

def prepare_intelligence(db,key="p46"):
    recovery,c,d,intel,_=seed_dispute(db,key)
    intel.process_evidence(c.recovery_case_id,d.dispute_id,"ev-p45-doc","provider-user")
    intel.build_snapshot(c.recovery_case_id,d.dispute_id,"finance-op")
    intel.run_recommendation(c.recovery_case_id,d.dispute_id,"finance-op",idempotency_key=f"{key}-recommend")
    comparisons=intel.repo.comparisons(d.dispute_id);material=[x.comparison_id for x in comparisons if x.severity=="material" and x.comparison_type in {"contradictory","changed"}]
    rag=intel.repo.rag_runs(d.dispute_id)[-1];items=intel.repo.rag_items(rag.run_id);checkpoints=intel.repo.checkpoints(d.dispute_id)
    return recovery,c,d,intel,material,[items[0].item_id], [checkpoints[-1].checkpoint_id]

def test_evidence_bound_packet_blocks_unresolved_policy_conflict_then_locks_when_resolved():
    f=factory()
    with f() as db:
        recovery,c,d,intel,material,citations,cps=prepare_intelligence(db,"conflict");svc=ProviderDisputeResolutionService(db,"tenant-a");c=recovery.repo.case(c.recovery_case_id)
        p=svc.save_packet(c.recovery_case_id,d.dispute_id,"finance-approver",outcome="reduce_recovery",amended_target_amount=Decimal("100"),rationale="Independent human finance approver reviews the locked provider evidence, recovery position, agreement and policy citations before changing the recovery target.",reason_codes=["provider_evidence_changes_recovery"],citation_refs=citations,resolved_comparison_refs=[],checkpoint_refs=cps,recommendation_disagreement_reason=None,expected_case_version=c.case_version,expected_packet_version=None,idempotency_key="p46-conflict-packet")
        assert "unresolved_material_policy_conflicts" in p.blocker_codes
        with pytest.raises(ReviewConflictError):svc.lock_packet(c.recovery_case_id,d.dispute_id,p.packet_id,"finance-approver",expected_packet_version=1,idempotency_key="p46-conflict-lock")
        p2=svc.save_packet(c.recovery_case_id,d.dispute_id,"finance-approver",outcome="reduce_recovery",amended_target_amount=Decimal("100"),rationale="Independent human finance approver resolves every material provider-evidence and payment-policy contradiction with citation-bound review before final resolution.",reason_codes=["provider_evidence_changes_recovery"],citation_refs=citations,resolved_comparison_refs=material,checkpoint_refs=cps,recommendation_disagreement_reason="The human reviewer resolves the cited material conflicts and documents why the final recovery target differs from the recommendation-only agent output.",expected_case_version=c.case_version,expected_packet_version=1,idempotency_key="p46-resolved-packet")
        p2=svc.lock_packet(c.recovery_case_id,d.dispute_id,p2.packet_id,"finance-approver",expected_packet_version=2,idempotency_key="p46-resolved-lock");assert p2.status=="pending_second_review" and p2.locked_payload_sha256

def test_material_reduction_requires_second_independent_human_and_creates_supersession_referral_correspondence():
    f=factory()
    with f() as db:
        recovery,c,d,intel,material,citations,cps=prepare_intelligence(db,"final");svc=ProviderDisputeResolutionService(db,"tenant-a");c=recovery.repo.case(c.recovery_case_id)
        p=svc.save_packet(c.recovery_case_id,d.dispute_id,"finance-approver",outcome="reduce_recovery",amended_target_amount=Decimal("100"),rationale="Independent primary human finance approver concludes the cited provider evidence and effective reimbursement policy support a reduced governed recovery target.",reason_codes=["validated_provider_evidence","policy_review_complete"],citation_refs=citations,resolved_comparison_refs=material,checkpoint_refs=cps,recommendation_disagreement_reason="The human reviewer independently weighs the contract and provider evidence and documents any divergence from the recommendation-only analysis.",expected_case_version=c.case_version,expected_packet_version=None,idempotency_key="p46-final-packet")
        p=svc.lock_packet(c.recovery_case_id,d.dispute_id,p.packet_id,"finance-approver",expected_packet_version=1,idempotency_key="p46-final-lock")
        with pytest.raises(ReviewConflictError):svc.close(c.recovery_case_id,d.dispute_id,p.packet_id,"finance-approver",expected_packet_version=1,expected_case_version=c.case_version,idempotency_key="p46-close-too-early")
        with pytest.raises(ReviewConflictError):svc.second_review(c.recovery_case_id,d.dispute_id,p.packet_id,"finance-approver",action="approve",rationale="The same human cannot provide material dispute dual control.",expected_packet_version=1,idempotency_key="p46-self-second")
        svc.second_review(c.recovery_case_id,d.dispute_id,p.packet_id,"finance-approver-2",action="approve",rationale="A second independent human finance approver confirms the locked evidence, citations, policy-conflict resolution and amended recovery target.",expected_packet_version=1,idempotency_key="p46-second")
        final=svc.close(c.recovery_case_id,d.dispute_id,p.packet_id,"finance-approver",expected_packet_version=1,expected_case_version=c.case_version,idempotency_key="p46-final-close")
        current=recovery.repo.case(c.recovery_case_id);assert current.target_recovery_amount==Decimal("100.00") and current.status=="recovery_amended";assert recovery.repo.disputes(c.recovery_case_id)[0].status=="resolved"
        snap=svc.snapshot(c.recovery_case_id,d.dispute_id,"finance-approver");assert final.reversal_referral_id and final.correspondence_id;assert len(snap["position_versions"])==2;assert snap["position_versions"][1]["previous_payload_sha256"]==snap["position_versions"][0]["payload_sha256"];assert snap["reversal_referrals"][0]["status"]=="pending_human_finance_action"
        assert intel.repo.checkpoints(d.dispute_id)[-1].status=="completed";assert recovery.repo.correspondence(c.recovery_case_id)[-1].body_sha256

def test_recommendation_disagreement_requires_explicit_human_reason():
    f=factory()
    with f() as db:
        recovery,c,d,intel,material,citations,cps=prepare_intelligence(db,"disagree");svc=ProviderDisputeResolutionService(db,"tenant-a");c=recovery.repo.case(c.recovery_case_id)
        rec=intel.repo.recommendation_runs(d.dispute_id)[-1]
        outcome="uphold_recovery" if rec.recommendation!="uphold_recovery" else "reduce_recovery";amount=c.target_recovery_amount if outcome=="uphold_recovery" else Decimal("100")
        p=svc.save_packet(c.recovery_case_id,d.dispute_id,"finance-approver",outcome=outcome,amended_target_amount=amount,rationale="The independent human reviewer reaches a different conclusion after examining the exact cited provider agreement, policy version and recovery evidence.",reason_codes=["human_evidence_judgment"],citation_refs=citations,resolved_comparison_refs=material,checkpoint_refs=cps,recommendation_disagreement_reason=None,expected_case_version=c.case_version,expected_packet_version=None,idempotency_key="p46-disagree")
        if p.recommendation_disagreement:
            assert "recommendation_disagreement_reason_required" in p.blocker_codes
            with pytest.raises(ReviewConflictError):svc.lock_packet(c.recovery_case_id,d.dispute_id,p.packet_id,"finance-approver",expected_packet_version=1,idempotency_key="p46-disagree-lock")

def test_old_release44_direct_resolution_path_is_retired_fail_closed():
    f=factory()
    with f() as db:
        recovery,c,d,_,_,_,_=prepare_intelligence(db,"retired")
        with pytest.raises(ReviewConflictError,match="retired"):recovery.resolve_dispute(c.recovery_case_id,d.dispute_id,"finance-approver",outcome="uphold_recovery",rationale="Legacy direct resolution must be blocked once the evidence-bound resolution workflow exists.",resolution_amount=c.target_recovery_amount,idempotency_key="legacy")

def test_release46_authority_migration_and_traceability_contracts():
    domain=Path("app/domain/provider_dispute_resolution.py").read_text();service=Path("app/services/provider_dispute_resolution.py").read_text();migration=Path("alembic/versions/0041_provider_dispute_resolution_recovery_amendment.py").read_text();old=Path("app/services/recovery_operations.py").read_text()
    for token in ['"ai_can_resolve_dispute":False','"background_worker_can_change_accounting":False','"background_worker_can_authorize_payment":False','"background_worker_can_collect_funds":False','"background_worker_can_move_money":False']:assert token in domain
    assert 'down_revision="0040_provider_dispute_intelligence"' in migration and "FORCE ROW LEVEL SECURITY" in migration and "reject_provider_dispute_resolution_immutable_mutation" in migration
    assert "pending_human_finance_action" in service and "release41_accounting_human_review" in service and "direct provider dispute resolution is retired" in old
    forbidden=("_post_journal(","authorize_packet(","handoff(","collect_funds(","move_money(")
    assert not any(x in service for x in forbidden)

def test_accounting_reconciliation_verification_is_evidence_only_and_precedes_final_recovery_closure():
    f=factory()
    with f() as db:
        recovery,c,d,intel,material,citations,cps=prepare_intelligence(db,"closure");svc=ProviderDisputeResolutionService(db,"tenant-a");c=recovery.repo.case(c.recovery_case_id)
        p=svc.save_packet(c.recovery_case_id,d.dispute_id,"finance-approver",outcome="withdraw_recovery",amended_target_amount=Decimal("0"),rationale="Independent human finance review concludes the locked provider evidence and effective policy support withdrawing the governed recovery target.",reason_codes=["recovery_withdrawn_after_evidence_review"],citation_refs=citations,resolved_comparison_refs=material,checkpoint_refs=cps,recommendation_disagreement_reason="The human reviewer documents the independent evidence judgment relative to the recommendation-only output.",expected_case_version=c.case_version,expected_packet_version=None,idempotency_key="p46-close-packet")
        svc.lock_packet(c.recovery_case_id,d.dispute_id,p.packet_id,"finance-approver",expected_packet_version=1,idempotency_key="p46-close-lock");svc.second_review(c.recovery_case_id,d.dispute_id,p.packet_id,"finance-approver-2",action="approve",rationale="Second independent human finance approver confirms the locked withdrawal packet and recovery-target amendment.",expected_packet_version=1,idempotency_key="p46-close-second");svc.close(c.recovery_case_id,d.dispute_id,p.packet_id,"finance-approver",expected_packet_version=1,expected_case_version=c.case_version,idempotency_key="p46-close-resolution")
        current=recovery.repo.case(c.recovery_case_id);lease=recovery.acquire_lease(c.recovery_case_id,"finance-op",expected_case_version=current.case_version);current=lease["case"];ref=svc.repo.referrals(c.recovery_case_id)[0]
        with pytest.raises(ReviewConflictError):svc.finalize_recovery_case(c.recovery_case_id,d.dispute_id,"finance-op",rationale="Recovery must not close before the reversal referral has verified downstream accounting/reconciliation evidence.",expected_case_version=current.case_version,lease_token=lease["lease_token"],idempotency_key="p46-premature-finalize")
        svc.verify_reconciliation_referral(c.recovery_case_id,d.dispute_id,ref.reversal_referral_id,"finance-op",status="verified",external_reference="ACCOUNTING-VERIFY-46",expected_case_version=current.case_version,lease_token=lease["lease_token"],idempotency_key="p46-referral-verified")
        current=recovery.repo.case(c.recovery_case_id);closed=svc.finalize_recovery_case(c.recovery_case_id,d.dispute_id,"finance-op",rationale="Human recovery investigator closes the case only after the evidence-bound dispute resolution and separately governed accounting/reconciliation amendment outcome are verified.",expected_case_version=current.case_version,lease_token=lease["lease_token"],idempotency_key="p46-final-recovery-close")
        assert closed.status=="closed" and closed.closure_reason_code=="provider_dispute_resolved";assert svc.repo.referrals(c.recovery_case_id)[0].status=="verified"
