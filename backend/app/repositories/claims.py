from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import set_tenant_context
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


class _TenantRepository:
    def __init__(self, session: Session, tenant_id: str) -> None:
        self.session = session
        self.tenant_id = tenant_id
        set_tenant_context(session, tenant_id)

    def _ensure_tenant(self, row_tenant_id: str) -> None:
        if row_tenant_id != self.tenant_id:
            raise ValueError("row tenant does not match repository tenant context")


class PatientRepository(_TenantRepository):
    def get(self, patient_id: str) -> PatientModel | None:
        return self.session.scalar(
            select(PatientModel).where(
                PatientModel.tenant_id == self.tenant_id,
                PatientModel.patient_id == patient_id,
            )
        )

    def get_by_subject(self, patient_subject_id: str) -> PatientModel | None:
        return self.session.scalar(
            select(PatientModel).where(
                PatientModel.tenant_id == self.tenant_id,
                PatientModel.patient_subject_id == patient_subject_id,
            )
        )

    def add(self, model: PatientModel) -> PatientModel:
        self._ensure_tenant(model.tenant_id)
        self.session.add(model)
        self.session.flush()
        return model


class ProviderRepository(_TenantRepository):
    def get(self, provider_id: str) -> ProviderModel | None:
        return self.session.scalar(
            select(ProviderModel).where(
                ProviderModel.tenant_id == self.tenant_id,
                ProviderModel.provider_id == provider_id,
            )
        )

    def add(self, model: ProviderModel) -> ProviderModel:
        self._ensure_tenant(model.tenant_id)
        self.session.add(model)
        self.session.flush()
        return model


class PolicyRepository(_TenantRepository):
    def get(self, policy_id: str) -> PolicyModel | None:
        return self.session.scalar(
            select(PolicyModel).where(
                PolicyModel.tenant_id == self.tenant_id,
                PolicyModel.policy_id == policy_id,
            )
        )

    def add(self, model: PolicyModel) -> PolicyModel:
        self._ensure_tenant(model.tenant_id)
        self.session.add(model)
        self.session.flush()
        return model


class EncounterRepository(_TenantRepository):
    def get(self, encounter_id: str) -> EncounterModel | None:
        return self.session.scalar(
            select(EncounterModel).where(
                EncounterModel.tenant_id == self.tenant_id,
                EncounterModel.encounter_id == encounter_id,
            )
        )

    def add(self, model: EncounterModel) -> EncounterModel:
        self._ensure_tenant(model.tenant_id)
        self.session.add(model)
        self.session.flush()
        return model


class ClaimRepository(_TenantRepository):
    def get(self, claim_id: str) -> ClaimModel | None:
        return self.session.scalar(
            select(ClaimModel).where(
                ClaimModel.tenant_id == self.tenant_id,
                ClaimModel.claim_id == claim_id,
            )
        )

    def get_for_update(self, claim_id: str) -> ClaimModel | None:
        return self.session.scalar(
            select(ClaimModel)
            .where(
                ClaimModel.tenant_id == self.tenant_id,
                ClaimModel.claim_id == claim_id,
            )
            .with_for_update()
        )

    def get_by_external_ref(self, external_claim_ref: str) -> ClaimModel | None:
        return self.session.scalar(
            select(ClaimModel).where(
                ClaimModel.tenant_id == self.tenant_id,
                ClaimModel.external_claim_ref == external_claim_ref,
            )
        )

    def list(self, *, status: str | None = None) -> list[ClaimModel]:
        statement = select(ClaimModel).where(ClaimModel.tenant_id == self.tenant_id)
        if status is not None:
            statement = statement.where(ClaimModel.status == status)
        return list(self.session.scalars(statement.order_by(ClaimModel.claim_id)))

    def add(self, model: ClaimModel) -> ClaimModel:
        self._ensure_tenant(model.tenant_id)
        self.session.add(model)
        self.session.flush()
        return model


class ClaimLineRepository(_TenantRepository):
    def list_for_claim(self, claim_id: str) -> list[ClaimLineModel]:
        return list(
            self.session.scalars(
                select(ClaimLineModel)
                .where(
                    ClaimLineModel.tenant_id == self.tenant_id,
                    ClaimLineModel.claim_id == claim_id,
                )
                .order_by(ClaimLineModel.line_number)
            )
        )

    def add(self, model: ClaimLineModel) -> ClaimLineModel:
        self._ensure_tenant(model.tenant_id)
        self.session.add(model)
        self.session.flush()
        return model


class EvidenceRepository(_TenantRepository):
    def get(self, evidence_id: str) -> EvidenceArtifactModel | None:
        return self.session.scalar(
            select(EvidenceArtifactModel).where(
                EvidenceArtifactModel.tenant_id == self.tenant_id,
                EvidenceArtifactModel.evidence_id == evidence_id,
            )
        )

    def get_by_content_hash(self, claim_id: str, content_sha256: str) -> EvidenceArtifactModel | None:
        return self.session.scalar(
            select(EvidenceArtifactModel).where(
                EvidenceArtifactModel.tenant_id == self.tenant_id,
                EvidenceArtifactModel.claim_id == claim_id,
                EvidenceArtifactModel.content_sha256 == content_sha256,
            )
        )

    def list_for_claim(self, claim_id: str) -> list[EvidenceArtifactModel]:
        return list(
            self.session.scalars(
                select(EvidenceArtifactModel)
                .where(
                    EvidenceArtifactModel.tenant_id == self.tenant_id,
                    EvidenceArtifactModel.claim_id == claim_id,
                )
                .order_by(EvidenceArtifactModel.evidence_id)
            )
        )

    def add(self, model: EvidenceArtifactModel) -> EvidenceArtifactModel:
        self._ensure_tenant(model.tenant_id)
        self.session.add(model)
        self.session.flush()
        return model


class EvidenceLineageRepository(_TenantRepository):
    def add(self, model: EvidenceLineageModel) -> EvidenceLineageModel:
        self._ensure_tenant(model.tenant_id)
        self.session.add(model)
        self.session.flush()
        return model

    def list_for_evidence(self, evidence_id: str) -> list[EvidenceLineageModel]:
        return list(
            self.session.scalars(
                select(EvidenceLineageModel).where(
                    EvidenceLineageModel.tenant_id == self.tenant_id,
                    (
                        (EvidenceLineageModel.child_evidence_id == evidence_id)
                        | (EvidenceLineageModel.parent_evidence_id == evidence_id)
                    ),
                )
            )
        )


class ClaimStatusEventRepository(_TenantRepository):
    def get_by_idempotency(self, idempotency_key: str) -> ClaimStatusEventModel | None:
        return self.session.scalar(
            select(ClaimStatusEventModel).where(
                ClaimStatusEventModel.tenant_id == self.tenant_id,
                ClaimStatusEventModel.idempotency_key == idempotency_key,
            )
        )

    def list_for_claim(self, claim_id: str) -> list[ClaimStatusEventModel]:
        return list(
            self.session.scalars(
                select(ClaimStatusEventModel)
                .where(
                    ClaimStatusEventModel.tenant_id == self.tenant_id,
                    ClaimStatusEventModel.claim_id == claim_id,
                )
                .order_by(ClaimStatusEventModel.to_version)
            )
        )

    def add(self, model: ClaimStatusEventModel) -> ClaimStatusEventModel:
        self._ensure_tenant(model.tenant_id)
        self.session.add(model)
        self.session.flush()
        return model


class HumanDecisionRepository(_TenantRepository):
    def get_by_idempotency(self, idempotency_key: str) -> HumanReviewDecisionModel | None:
        return self.session.scalar(
            select(HumanReviewDecisionModel).where(
                HumanReviewDecisionModel.tenant_id == self.tenant_id,
                HumanReviewDecisionModel.idempotency_key == idempotency_key,
            )
        )

    def add(self, model: HumanReviewDecisionModel) -> HumanReviewDecisionModel:
        self._ensure_tenant(model.tenant_id)
        self.session.add(model)
        self.session.flush()
        return model


class AuditEventRepository(_TenantRepository):
    def get_by_idempotency(self, idempotency_key: str) -> AuditEventModel | None:
        return self.session.scalar(
            select(AuditEventModel).where(
                AuditEventModel.tenant_id == self.tenant_id,
                AuditEventModel.idempotency_key == idempotency_key,
            )
        )

    def add(self, model: AuditEventModel) -> AuditEventModel:
        self._ensure_tenant(model.tenant_id)
        self.session.add(model)
        self.session.flush()
        return model

    def list_for_resource(self, resource_type: str, resource_id: str) -> list[AuditEventModel]:
        return list(
            self.session.scalars(
                select(AuditEventModel)
                .where(
                    AuditEventModel.tenant_id == self.tenant_id,
                    AuditEventModel.resource_type == resource_type,
                    AuditEventModel.resource_id == resource_id,
                )
                .order_by(AuditEventModel.occurred_at, AuditEventModel.audit_event_id)
            )
        )
