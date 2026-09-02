from __future__ import annotations
from datetime import UTC, datetime
from uuid import uuid4
from sqlalchemy.orm import Session
from app.domain.regulatory_lessons_learned import LESSONS_LEARNED_AUTHORITY
from app.models.regulatory_lessons_learned import *
from app.repositories.regulatory_lessons_learned import RegulatoryLessonsLearnedRepository
from app.repositories.tenancy import MembershipRepository
from app.services.review_workbench import ReviewConflictError


def _now(): return datetime.now(UTC)


class RegulatoryLessonsLearnedService:
    READ = {"auditor", "tenant_admin", "accounting_controller"}
    ANALYST = READ
    APPROVER = {"tenant_admin", "accounting_controller"}

    def __init__(self, session: Session, tenant_id: str):
        self.session = session; self.tenant_id = tenant_id
        self.repo = RegulatoryLessonsLearnedRepository(session, tenant_id)
        self.members = MembershipRepository(session, tenant_id)

    def _role(self, user_id, allowed, msg):
        m = self.members.get_by_user(user_id)
        if m is None or m.status != "active" or m.role not in allowed: raise ReviewConflictError(msg)
        return m

    @staticmethod
    def effectiveness_benchmark(*, outcome_success_rate: float, retest_pass_rate: float, recurrence_free_rate: float, sustainability_score: float) -> float:
        return round(max(0.0, min(1.0, outcome_success_rate * .30 + retest_pass_rate * .25 + recurrence_free_rate * .25 + sustainability_score * .20)), 4)

    @staticmethod
    def improvement_priority(*, recurrence_risk: float, control_criticality: float, cross_entity_exposure: float, regulator_relevance: float) -> float:
        return round(max(0.0, min(100.0, 100 * (recurrence_risk * .35 + control_criticality * .30 + cross_entity_exposure * .20 + regulator_relevance * .15))), 2)

    def create_lesson(self, user_id, **p):
        self._role(user_id, self.ANALYST, "authorized lessons-learned analyst required")
        version = len(self.repo.lessons(p["lesson_key"])) + 1
        return self.repo.add(RegulatoryRemediationLessonModel(
            lesson_id=f"rll_{uuid4().hex}", tenant_id=self.tenant_id, version=version,
            status="candidate_human_review", created_by_user_id=user_id, created_at=_now(), **p))

    def ingest_feedback(self, user_id, **p):
        self._role(user_id, self.ANALYST, "authorized regulatory-feedback analyst required")
        if not p.get("evidence_refs"): raise ReviewConflictError("regulatory feedback requires authoritative evidence")
        return self.repo.add(RegulatoryFeedbackObservationModel(
            feedback_id=f"rfo_{uuid4().hex}", tenant_id=self.tenant_id, created_at=_now(), **p))

    def propose_improvement(self, user_id, **p):
        self._role(user_id, self.ANALYST, "authorized control-improvement analyst required")
        if self.repo.lesson(p["lesson_id"]) is None: raise LookupError("lesson not found")
        return self.repo.add(ControlImprovementProposalModel(
            proposal_id=f"cip_{uuid4().hex}", tenant_id=self.tenant_id, status="proposed",
            human_approval_required=True, proposed_by_user_id=user_id, proposed_at=_now(), **p))

    def decide_improvement(self, user_id, proposal_id: str, *, decision: str, rationale: str, approval_refs: list):
        self._role(user_id, self.APPROVER, "authorized human control-improvement approver required")
        proposal = self.repo.proposal(proposal_id)
        if proposal is None: raise LookupError("control improvement proposal not found")
        if proposal.proposed_by_user_id == user_id: raise ReviewConflictError("segregation of duties: proposer cannot approve own proposal")
        if decision == "approve" and not approval_refs: raise ReviewConflictError("human approval evidence is required")
        proposal.status = "human_approved" if decision == "approve" else "rejected" if decision == "reject" else "revision_required"
        self.session.flush()
        return self.repo.add(ControlImprovementDecisionModel(
            decision_id=f"cid_{uuid4().hex}", tenant_id=self.tenant_id, proposal_id=proposal_id,
            decision=decision, rationale=rationale, approval_refs=approval_refs,
            decided_by_user_id=user_id, decided_at=_now()))

    def promote_knowledge(self, user_id, **p):
        self._role(user_id, self.APPROVER, "authorized human knowledge-governance approver required")
        lesson = self.repo.lesson(p["lesson_id"])
        if lesson is None: raise LookupError("lesson not found")
        if not p.get("approved_refs") or not p.get("source_hashes"): raise ReviewConflictError("approved evidence and source hashes required")
        return self.repo.add(KnowledgePromotionModel(
            promotion_id=f"rkp_{uuid4().hex}", tenant_id=self.tenant_id, status="human_approved_for_indexing",
            promoted_by_user_id=user_id, promoted_at=_now(), **p))

    def dashboard(self, user_id):
        self._role(user_id, self.READ, "lessons-learned read role required")
        lessons, feedback, proposals, decisions, promotions = self.repo.lessons(), self.repo.feedback(), self.repo.proposals(), self.repo.decisions(), self.repo.promotions()
        return {
            "lesson_versions": len(lessons), "regulatory_feedback_observations": len(feedback),
            "control_improvement_proposals": len(proposals), "human_approved_improvements": sum(p.status == "human_approved" for p in proposals),
            "knowledge_promotions": len(promotions), "human_decisions": len(decisions),
            "authority": LESSONS_LEARNED_AUTHORITY,
        }
