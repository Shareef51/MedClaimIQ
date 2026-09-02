from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.access import Permission, ROLE_PERMISSIONS, UserRole
from app.domain.claims import ActorType, ClaimStatus, HumanDecision, can_transition
from app.models.claims import (
    AuditEventModel,
    ClaimLineModel,
    ClaimModel,
    ClaimStatusEventModel,
    EncounterModel,
    EvidenceArtifactModel,
    EvidenceLineageModel,
    HumanReviewDecisionModel,
    PatientModel,
    PolicyModel,
    ProviderModel,
)
from app.models.tenancy import OrganizationModel
from app.domain.realtime import EventEnvelope, EventTopic
from app.realtime.events import enqueue_realtime_event
from app.repositories.claims import (
    AuditEventRepository,
    ClaimLineRepository,
    ClaimRepository,
    ClaimStatusEventRepository,
    EncounterRepository,
    EvidenceLineageRepository,
    EvidenceRepository,
    HumanDecisionRepository,
    PatientRepository,
    PolicyRepository,
    ProviderRepository,
)
from app.repositories.tenancy import MembershipRepository
from app.schemas.claims import (
    ClaimCreate,
    ClaimLineCreate,
    ClaimTransitionRequest,
    EncounterCreate,
    EvidenceCreate,
    EvidenceLineageCreate,
    HumanDecisionCreate,
    PatientCreate,
    PolicyCreate,
    ProviderCreate,
)


class ClaimDomainInvariantError(ValueError):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _derived_idempotency(base: str, suffix: str) -> str:
    candidate = f"{base}:{suffix}"
    if len(candidate) <= 160:
        return candidate
    digest = hashlib.sha256(candidate.encode("utf-8")).hexdigest()
    return f"derived:{digest}"


class ClaimDomainService:
    """Transaction-scoped service enforcing claim/evidence invariants.

    Callers own commit/rollback. Every read/write remains explicitly tenant-scoped;
    PostgreSQL RLS independently enforces the same boundary.
    """

    def __init__(self, session: Session, tenant_id: str) -> None:
        self.session = session
        self.tenant_id = tenant_id
        self.patients = PatientRepository(session, tenant_id)
        self.providers = ProviderRepository(session, tenant_id)
        self.policies = PolicyRepository(session, tenant_id)
        self.encounters = EncounterRepository(session, tenant_id)
        self.claims = ClaimRepository(session, tenant_id)
        self.claim_lines = ClaimLineRepository(session, tenant_id)
        self.evidence = EvidenceRepository(session, tenant_id)
        self.lineage = EvidenceLineageRepository(session, tenant_id)
        self.status_events = ClaimStatusEventRepository(session, tenant_id)
        self.decisions = HumanDecisionRepository(session, tenant_id)
        self.audit = AuditEventRepository(session, tenant_id)

    def create_patient(self, payload: PatientCreate) -> PatientModel:
        if self.patients.get(payload.patient_id) or self.patients.get_by_subject(payload.patient_subject_id):
            raise ClaimDomainInvariantError("patient already exists in this tenant")
        return self.patients.add(
            PatientModel(
                patient_id=payload.patient_id,
                tenant_id=self.tenant_id,
                patient_subject_id=payload.patient_subject_id,
                external_identifiers=payload.external_identifiers,
                status="active",
                synthetic_data=payload.synthetic_data,
            )
        )

    def create_provider(self, payload: ProviderCreate) -> ProviderModel:
        self._require_organization(payload.organization_id)
        if self.providers.get(payload.provider_id):
            raise ClaimDomainInvariantError("provider already exists in this tenant")
        return self.providers.add(
            ProviderModel(
                provider_id=payload.provider_id,
                tenant_id=self.tenant_id,
                organization_id=payload.organization_id,
                provider_ref=payload.provider_ref,
                provider_type=payload.provider_type,
                external_identifiers=payload.external_identifiers,
            )
        )

    def create_policy(self, payload: PolicyCreate) -> PolicyModel:
        self._require_patient_subject(payload.patient_subject_id)
        self._require_organization(payload.payer_organization_id)
        if self.policies.get(payload.policy_id):
            raise ClaimDomainInvariantError("policy already exists in this tenant")
        return self.policies.add(
            PolicyModel(
                policy_id=payload.policy_id,
                tenant_id=self.tenant_id,
                patient_subject_id=payload.patient_subject_id,
                payer_organization_id=payload.payer_organization_id,
                policy_ref=payload.policy_ref,
                plan_name=payload.plan_name,
                effective_from=payload.effective_from,
                effective_to=payload.effective_to,
                status="active",
                policy_version=payload.policy_version,
                source_system=payload.source_system,
            )
        )

    def create_encounter(self, payload: EncounterCreate) -> EncounterModel:
        self._require_patient_subject(payload.patient_subject_id)
        self._require_organization(payload.provider_organization_id)
        if self.encounters.get(payload.encounter_id):
            raise ClaimDomainInvariantError("encounter already exists in this tenant")
        return self.encounters.add(
            EncounterModel(
                encounter_id=payload.encounter_id,
                tenant_id=self.tenant_id,
                patient_subject_id=payload.patient_subject_id,
                provider_organization_id=payload.provider_organization_id,
                encounter_ref=payload.encounter_ref,
                encounter_type=payload.encounter_type,
                started_at=payload.started_at,
                ended_at=payload.ended_at,
                source_system=payload.source_system,
                external_identifiers=payload.external_identifiers,
            )
        )

    def create_claim(self, payload: ClaimCreate) -> ClaimModel:
        previous = self.audit.get_by_idempotency(payload.idempotency_key)
        if previous is not None:
            if previous.action != "claim.created" or previous.resource_id != payload.claim_id:
                raise ClaimDomainInvariantError("idempotency key was already used for another operation")
            existing = self.claims.get(payload.claim_id)
            if existing is None:
                raise ClaimDomainInvariantError("idempotency record exists without its claim")
            return existing

        if self.claims.get(payload.claim_id) or self.claims.get_by_external_ref(payload.external_claim_ref):
            raise ClaimDomainInvariantError("claim already exists in this tenant")
        self._require_patient_subject(payload.patient_subject_id)
        self._require_organization(payload.provider_organization_id)
        self._require_organization(payload.payer_organization_id)

        if payload.policy_id:
            policy = self.policies.get(payload.policy_id)
            if policy is None or policy.patient_subject_id != payload.patient_subject_id:
                raise ClaimDomainInvariantError("policy must belong to the same tenant and patient")
            if payload.service_from < policy.effective_from or (
                policy.effective_to is not None and payload.service_from > policy.effective_to
            ):
                raise ClaimDomainInvariantError("claim service date is outside policy effective window")
        if payload.encounter_id:
            encounter = self.encounters.get(payload.encounter_id)
            if encounter is None or encounter.patient_subject_id != payload.patient_subject_id:
                raise ClaimDomainInvariantError("encounter must belong to the same tenant and patient")
            if encounter.provider_organization_id != payload.provider_organization_id:
                raise ClaimDomainInvariantError("encounter provider must match the claim provider")
        if payload.assigned_reviewer_user_id:
            self._require_claim_reviewer(payload.assigned_reviewer_user_id)

        claim = self.claims.add(
            ClaimModel(
                claim_id=payload.claim_id,
                tenant_id=self.tenant_id,
                external_claim_ref=payload.external_claim_ref,
                patient_subject_id=payload.patient_subject_id,
                provider_organization_id=payload.provider_organization_id,
                payer_organization_id=payload.payer_organization_id,
                policy_id=payload.policy_id,
                encounter_id=payload.encounter_id,
                claim_type=payload.claim_type,
                status=ClaimStatus.SUBMITTED.value,
                status_version=1,
                assigned_reviewer_user_id=payload.assigned_reviewer_user_id,
                total_amount=payload.total_amount,
                currency=payload.currency,
                service_from=payload.service_from,
                service_to=payload.service_to,
            )
        )
        self._append_audit(
            action="claim.created",
            resource_type="claim",
            resource_id=claim.claim_id,
            actor_type=payload.created_by_actor_type,
            actor_id=payload.created_by_actor_id,
            idempotency_key=payload.idempotency_key,
            trace_id=payload.trace_id,
            details={"status": claim.status, "status_version": claim.status_version},
        )
        return claim

    def add_claim_line(self, claim_id: str, payload: ClaimLineCreate) -> ClaimLineModel:
        claim = self._require_claim(claim_id)
        if payload.service_date < claim.service_from or (
            claim.service_to is not None and payload.service_date > claim.service_to
        ):
            raise ClaimDomainInvariantError("claim line service date is outside the claim service window")
        if payload.provider_id:
            provider = self.providers.get(payload.provider_id)
            if provider is None:
                raise ClaimDomainInvariantError("claim line provider must belong to the claim tenant")
            if provider.organization_id != claim.provider_organization_id:
                raise ClaimDomainInvariantError("claim line provider organization must match the claim")
        return self.claim_lines.add(
            ClaimLineModel(
                claim_line_id=payload.claim_line_id,
                tenant_id=self.tenant_id,
                claim_id=claim_id,
                line_number=payload.line_number,
                code_system=payload.code_system,
                service_code=payload.service_code,
                description=payload.description,
                service_date=payload.service_date,
                units=payload.units,
                amount=payload.amount,
                provider_id=payload.provider_id,
            )
        )

    def add_evidence(self, payload: EvidenceCreate) -> EvidenceArtifactModel:
        previous = self.audit.get_by_idempotency(payload.idempotency_key)
        if previous is not None:
            if previous.action != "evidence.created" or previous.resource_id != payload.evidence_id:
                raise ClaimDomainInvariantError("idempotency key was already used for another operation")
            existing = self.evidence.get(payload.evidence_id)
            if existing is None:
                raise ClaimDomainInvariantError("idempotency record exists without its evidence")
            return existing

        claim = self._require_claim(payload.claim_id)
        duplicate = self.evidence.get_by_content_hash(payload.claim_id, payload.content_sha256.lower())
        if duplicate is not None:
            return duplicate
        evidence = self.evidence.add(
            EvidenceArtifactModel(
                evidence_id=payload.evidence_id,
                tenant_id=self.tenant_id,
                claim_id=payload.claim_id,
                patient_subject_id=claim.patient_subject_id,
                source_type=payload.source_type.value,
                source_system=payload.source_system,
                source_locator=payload.source_locator,
                document_type=payload.document_type,
                media_type=payload.media_type,
                object_key=payload.object_key,
                storage_etag=payload.storage_etag,
                storage_version_id=payload.storage_version_id,
                content_sha256=payload.content_sha256.lower(),
                byte_size=payload.byte_size,
                status=payload.status.value,
                evidence_version=payload.evidence_version,
                uploaded_by_user_id=payload.uploaded_by_user_id,
                captured_at=payload.captured_at,
                authoritative=payload.authoritative,
                media_metadata=payload.media_metadata,
                verified_at=payload.verified_at,
            )
        )
        self._append_audit(
            action="evidence.created",
            resource_type="evidence",
            resource_id=evidence.evidence_id,
            actor_type=payload.actor_type,
            actor_id=payload.actor_id,
            idempotency_key=payload.idempotency_key,
            trace_id=payload.trace_id,
            details={
                "claim_id": evidence.claim_id,
                "document_type": evidence.document_type,
                "source_type": evidence.source_type,
                "status": evidence.status,
                "content_sha256": evidence.content_sha256,
            },
        )
        return evidence

    def add_evidence_lineage(self, payload: EvidenceLineageCreate) -> EvidenceLineageModel:
        child = self.evidence.get(payload.child_evidence_id)
        parent = self.evidence.get(payload.parent_evidence_id)
        if child is None or parent is None:
            raise ClaimDomainInvariantError("both lineage artifacts must belong to the tenant")
        if child.claim_id != parent.claim_id:
            raise ClaimDomainInvariantError("lineage cannot cross claim boundaries")
        return self.lineage.add(
            EvidenceLineageModel(
                lineage_id=payload.lineage_id,
                tenant_id=self.tenant_id,
                claim_id=child.claim_id,
                child_evidence_id=child.evidence_id,
                parent_evidence_id=parent.evidence_id,
                relationship=payload.relationship.value,
                transformation_name=payload.transformation_name,
                transformation_version=payload.transformation_version,
                transformation_metadata=payload.transformation_metadata,
                created_at=_now(),
            )
        )

    def transition_claim(
        self, claim_id: str, payload: ClaimTransitionRequest
    ) -> ClaimStatusEventModel:
        return self._transition_claim(claim_id, payload, allow_final_human_transition=False)

    def record_human_decision(
        self, claim_id: str, payload: HumanDecisionCreate
    ) -> HumanReviewDecisionModel:
        existing = self.decisions.get_by_idempotency(payload.idempotency_key)
        if existing is not None:
            if existing.claim_id != claim_id or existing.decision != payload.decision.value:
                raise ClaimDomainInvariantError("idempotency key was already used for another decision")
            return existing

        claim = self.claims.get_for_update(claim_id)
        if claim is None:
            raise ClaimDomainInvariantError("claim does not exist in this tenant")
        if ClaimStatus(claim.status) is not ClaimStatus.HUMAN_REVIEW:
            raise ClaimDomainInvariantError("human decision requires claim status human_review")
        membership = self._require_claim_reviewer(payload.reviewer_user_id)
        if Permission.CLAIM_RECORD_HUMAN_DECISION not in ROLE_PERMISSIONS[UserRole(membership.role)]:
            raise ClaimDomainInvariantError("reviewer is not permitted to record a final human decision")
        if claim.assigned_reviewer_user_id not in {None, payload.reviewer_user_id}:
            raise ClaimDomainInvariantError("claim is assigned to another reviewer")
        for snapshot_item in payload.evidence_snapshot:
            evidence_id = snapshot_item.get("evidence_id")
            if not isinstance(evidence_id, str) or self.evidence.get(evidence_id) is None:
                raise ClaimDomainInvariantError(
                    "every human-decision evidence snapshot item must reference tenant-scoped evidence"
                )

        decision = self.decisions.add(
            HumanReviewDecisionModel(
                decision_id=payload.decision_id,
                tenant_id=self.tenant_id,
                claim_id=claim_id,
                reviewer_user_id=payload.reviewer_user_id,
                decision=payload.decision.value,
                rationale=payload.rationale,
                evidence_snapshot=payload.evidence_snapshot,
                idempotency_key=payload.idempotency_key,
                decided_at=_now(),
            )
        )
        self._append_audit(
            action="claim.human_decision_recorded",
            resource_type="claim",
            resource_id=claim_id,
            actor_type=ActorType.HUMAN,
            actor_id=payload.reviewer_user_id,
            idempotency_key=_derived_idempotency(payload.idempotency_key, "audit"),
            trace_id=payload.trace_id,
            details={"decision": payload.decision.value, "decision_id": payload.decision_id},
        )

        target = {
            HumanDecision.APPROVE: ClaimStatus.COMPLETED,
            HumanDecision.DENY: ClaimStatus.COMPLETED,
            HumanDecision.PARTIAL_APPROVE: ClaimStatus.COMPLETED,
            HumanDecision.REQUEST_INFORMATION: ClaimStatus.PENDING_EVIDENCE,
            HumanDecision.ESCALATE: ClaimStatus.HUMAN_REVIEW,
        }[payload.decision]
        if target is not ClaimStatus.HUMAN_REVIEW:
            self._transition_claim(
                claim_id,
                ClaimTransitionRequest(
                    status_event_id=f"status-{uuid4().hex}",
                    to_status=target,
                    actor_type=ActorType.HUMAN,
                    actor_id=payload.reviewer_user_id,
                    reason=f"Human reviewer decision: {payload.decision.value}",
                    idempotency_key=_derived_idempotency(payload.idempotency_key, "transition"),
                    trace_id=payload.trace_id,
                    expected_status_version=claim.status_version,
                ),
                allow_final_human_transition=True,
            )
        return decision

    def _transition_claim(
        self,
        claim_id: str,
        payload: ClaimTransitionRequest,
        *,
        allow_final_human_transition: bool,
    ) -> ClaimStatusEventModel:
        existing = self.status_events.get_by_idempotency(payload.idempotency_key)
        if existing is not None:
            if existing.claim_id != claim_id or existing.to_status != payload.to_status.value:
                raise ClaimDomainInvariantError("idempotency key was already used for another transition")
            return existing

        claim = self.claims.get_for_update(claim_id)
        if claim is None:
            raise ClaimDomainInvariantError("claim does not exist in this tenant")
        if payload.expected_status_version is not None and claim.status_version != payload.expected_status_version:
            raise ClaimDomainInvariantError("claim status version conflict")

        from_status = ClaimStatus(claim.status)
        if from_status is ClaimStatus.HUMAN_REVIEW and payload.to_status in {
            ClaimStatus.COMPLETED,
            ClaimStatus.APPEAL_READY,
        } and not allow_final_human_transition:
            raise ClaimDomainInvariantError("final claim transition requires a persisted human decision")
        if not can_transition(from_status, payload.to_status):
            raise ClaimDomainInvariantError(
                f"invalid claim transition: {from_status.value} -> {payload.to_status.value}"
            )

        from_version = claim.status_version
        claim.status = payload.to_status.value
        claim.status_version += 1
        if payload.to_status is ClaimStatus.AI_REVIEWED:
            claim.ai_review_completed_at = _now()
        if payload.to_status in {ClaimStatus.COMPLETED, ClaimStatus.APPEAL_READY}:
            claim.human_review_completed_at = _now()
        event = self.status_events.add(
            ClaimStatusEventModel(
                status_event_id=payload.status_event_id,
                tenant_id=self.tenant_id,
                claim_id=claim_id,
                from_status=from_status.value,
                to_status=payload.to_status.value,
                from_version=from_version,
                to_version=claim.status_version,
                actor_type=payload.actor_type.value,
                actor_id=payload.actor_id,
                reason=payload.reason,
                idempotency_key=payload.idempotency_key,
                trace_id=payload.trace_id,
                occurred_at=_now(),
            )
        )
        self._append_audit(
            action="claim.status_changed",
            resource_type="claim",
            resource_id=claim_id,
            actor_type=payload.actor_type,
            actor_id=payload.actor_id,
            idempotency_key=_derived_idempotency(payload.idempotency_key, "audit"),
            trace_id=payload.trace_id,
            details={
                "from_status": from_status.value,
                "to_status": payload.to_status.value,
                "from_version": from_version,
                "to_version": claim.status_version,
            },
        )
        self.session.flush()
        return event

    def _require_claim(self, claim_id: str) -> ClaimModel:
        claim = self.claims.get(claim_id)
        if claim is None:
            raise ClaimDomainInvariantError("claim does not exist in this tenant")
        return claim

    def _require_patient_subject(self, patient_subject_id: str) -> PatientModel:
        patient = self.patients.get_by_subject(patient_subject_id)
        if patient is None or patient.status != "active":
            raise ClaimDomainInvariantError("patient must belong to the tenant and be active")
        return patient

    def _require_organization(self, organization_id: str) -> OrganizationModel:
        organization = self.session.scalar(
            select(OrganizationModel).where(
                OrganizationModel.organization_id == organization_id,
                OrganizationModel.tenant_id == self.tenant_id,
                OrganizationModel.is_active.is_(True),
            )
        )
        if organization is None:
            raise ClaimDomainInvariantError("organization must belong to the tenant and be active")
        return organization

    def _require_claim_reviewer(self, user_id: str):
        membership = MembershipRepository(self.session, self.tenant_id).get_by_user(user_id)
        if membership is None or membership.status != "active":
            raise ClaimDomainInvariantError("reviewer must be an active member of the tenant")
        if membership.role != UserRole.CLAIMS_REVIEWER.value:
            raise ClaimDomainInvariantError("user must have the claims_reviewer role")
        return membership

    def _append_audit(
        self,
        *,
        action: str,
        resource_type: str,
        resource_id: str,
        actor_type: ActorType,
        actor_id: str,
        idempotency_key: str,
        trace_id: str | None,
        details: dict[str, object],
    ) -> AuditEventModel:
        existing = self.audit.get_by_idempotency(idempotency_key)
        if existing is not None:
            return existing
        event = self.audit.add(
            AuditEventModel(
                audit_event_id=f"audit-{uuid4().hex}", tenant_id=self.tenant_id,
                actor_type=actor_type.value, actor_id=actor_id, action=action,
                resource_type=resource_type, resource_id=resource_id, trace_id=trace_id,
                idempotency_key=idempotency_key, details=details, occurred_at=_now(),
            )
        )
        claim_id = resource_id if resource_type == "claim" else details.get("claim_id")
        if isinstance(claim_id, str):
            enqueue_realtime_event(self.session, envelope=EventEnvelope(
                event_id=event.audit_event_id, event_type=action, tenant_id=self.tenant_id,
                claim_id=claim_id, aggregate_type=resource_type, aggregate_id=resource_id,
                occurred_at=event.occurred_at, trace_id=trace_id, producer="medclaimiq-claim-domain",
                payload={"actor_type": actor_type.value, "action": action},
                metadata={"audit_event_id": event.audit_event_id},
            ), topic=EventTopic.CLAIMS.value)
        return event
