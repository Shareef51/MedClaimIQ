from __future__ import annotations
from datetime import UTC, datetime
from uuid import uuid4
from sqlalchemy.orm import Session
from app.domain.regulatory_reopened_outcome_validation import REOPENED_OUTCOME_AUTHORITY
from app.models.regulatory_reopened_outcome_validation import *
from app.repositories.regulatory_reopened_outcome_validation import RegulatoryReopenedOutcomeRepository
from app.repositories.tenancy import MembershipRepository
from app.services.review_workbench import ReviewConflictError


def _now(): return datetime.now(UTC)


class RegulatoryReopenedOutcomeValidationService:
    READ = {"auditor", "tenant_admin", "accounting_controller"}
    ANALYST = READ
    EXECUTIVE = {"tenant_admin", "accounting_controller"}

    def __init__(self, session: Session, tenant_id: str):
        self.session = session
        self.tenant_id = tenant_id
        self.repo = RegulatoryReopenedOutcomeRepository(session, tenant_id)
        self.members = MembershipRepository(session, tenant_id)

    def _role(self, user_id, allowed, msg):
        m = self.members.get_by_user(user_id)
        if m is None or m.status != "active" or m.role not in allowed:
            raise ReviewConflictError(msg)
        return m

    @staticmethod
    def closure_readiness(*, current_effectiveness_score, containment_score, independent_validated, sustainability_complete, cross_entity_complete, commitments_complete, second_recurrence_count=0):
        score = current_effectiveness_score * 30 + containment_score * 25
        score += 15 if independent_validated else 0
        score += 10 if sustainability_complete else 0
        score += 10 if cross_entity_complete else 0
        score += 10 if commitments_complete else 0
        score -= min(second_recurrence_count, 3) * 15
        return round(max(0.0, min(100.0, score)), 2)

    @staticmethod
    def readiness_blockers(*, independent_validated, sustainability_complete, cross_entity_complete, commitments_complete, second_recurrence_count=0):
        blockers = []
        if not independent_validated: blockers.append("independent_revalidation_incomplete")
        if not sustainability_complete: blockers.append("sustainability_window_incomplete")
        if not cross_entity_complete: blockers.append("cross_entity_validation_incomplete")
        if not commitments_complete: blockers.append("renewed_regulatory_commitments_incomplete")
        if second_recurrence_count > 0: blockers.append("second_recurrence_requires_escalation")
        return blockers

    def register_outcome(self, user_id, **p):
        self._role(user_id, self.ANALYST, "authorized reopened-issue analyst required")
        if not p.get("renewed_remediation_refs") or not p.get("corrective_action_refs"):
            raise ReviewConflictError("renewed remediation and corrective-action references are required")
        return self.repo.add(ReopenedRemediationOutcomeModel(outcome_id=f"rro_{uuid4().hex}", tenant_id=self.tenant_id, status="remediating", created_at=_now(), **p))

    def record_revalidation(self, user_id, **p):
        self._role(user_id, self.EXECUTIVE, "authorized independent validation role required")
        if not p.get("retest_evidence_refs") or not p.get("independent_evidence_refs"):
            raise ReviewConflictError("retest and independent validation evidence are required")
        p["independently_validated"] = True
        p["validated_by_user_id"] = user_id
        p["validated_at"] = _now()
        return self.repo.add(ReopenedControlRevalidationModel(revalidation_id=f"rcv_{uuid4().hex}", tenant_id=self.tenant_id, **p))

    def create_assurance(self, user_id, **p):
        self._role(user_id, self.ANALYST, "authorized recurrence-closure analyst required")
        version = len(self.repo.assurances(p["deficiency_key"])) + 1
        blockers = self.readiness_blockers(
            independent_validated=p["independent_validated"], sustainability_complete=p["sustainability_complete"],
            cross_entity_complete=p["cross_entity_complete"], commitments_complete=p["commitments_complete"],
            second_recurrence_count=p.get("second_recurrence_count", 0),
        )
        score = self.closure_readiness(
            current_effectiveness_score=p["current_effectiveness_score"], containment_score=p["recurrence_containment_score"],
            independent_validated=p["independent_validated"], sustainability_complete=p["sustainability_complete"],
            cross_entity_complete=p["cross_entity_complete"], commitments_complete=p["commitments_complete"],
            second_recurrence_count=p.get("second_recurrence_count", 0),
        )
        status = "ready_for_human_recertification" if score >= 90 and not blockers else "blocked"
        return self.repo.add(RecurrenceClosureAssuranceModel(
            assurance_id=f"rca_{uuid4().hex}", tenant_id=self.tenant_id, deficiency_key=p["deficiency_key"], outcome_id=p["outcome_id"],
            version=version, revalidation_refs=p.get("revalidation_refs", []), sustainability_window_days=p.get("sustainability_window_days", 90),
            sustainability_evidence_refs=p.get("sustainability_evidence_refs", []), second_recurrence_count=p.get("second_recurrence_count", 0),
            second_recurrence_escalated=p.get("second_recurrence_count", 0) > 0, readiness_score=score, blockers=blockers, status=status, created_at=_now()))

    def recertify(self, user_id, assurance_id, *, decision, rationale, certification_refs):
        self._role(user_id, self.EXECUTIVE, "authorized human recertification authority required")
        a = self.repo.assurance(assurance_id)
        if a is None: raise LookupError("closure assurance not found")
        if decision == "reclose" and (a.readiness_score < 90 or a.blockers):
            raise ReviewConflictError("reclosure blocked until all independent validation, sustainability, cross-entity and commitment gates pass")
        if decision == "reclose" and not certification_refs:
            raise ReviewConflictError("human recertification requires certification evidence")
        a.status = "human_reclosed" if decision == "reclose" else "continued_monitoring" if decision == "monitor" else "remediation_extended"
        self.session.flush()
        return self.repo.add(ReopenedIssueRecertificationModel(
            recertification_id=f"rir_{uuid4().hex}", tenant_id=self.tenant_id, deficiency_key=a.deficiency_key, assurance_id=a.assurance_id,
            decision=decision, rationale=rationale, certification_refs=certification_refs, decided_by_user_id=user_id, decided_at=_now()))

    def dashboard(self, user_id):
        self._role(user_id, self.READ, "reopened outcome validation read role required")
        outcomes = self.repo.outcomes(); vals = self.repo.revalidations(); assurances = self.repo.assurances(); recerts = self.repo.recertifications()
        return {
            "reopened_outcomes": len(outcomes),
            "independent_revalidations": sum(v.independently_validated for v in vals),
            "assurance_versions": len(assurances),
            "ready_for_human_recertification": sum(a.status == "ready_for_human_recertification" for a in assurances),
            "second_recurrence_escalations": sum(a.second_recurrence_escalated for a in assurances),
            "human_reclosures": sum(r.decision == "reclose" for r in recerts),
            "authority": REOPENED_OUTCOME_AUTHORITY,
        }
