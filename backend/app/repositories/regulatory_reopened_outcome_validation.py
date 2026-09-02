from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import set_tenant_context
from app.models.regulatory_reopened_outcome_validation import *


class RegulatoryReopenedOutcomeRepository:
    def __init__(self, session: Session, tenant_id: str):
        self.session = session
        self.tenant_id = tenant_id
        set_tenant_context(session, tenant_id)

    def add(self, row):
        if row.tenant_id != self.tenant_id:
            raise ValueError("tenant mismatch")
        self.session.add(row)
        self.session.flush()
        return row

    def outcomes(self, key=None):
        q = select(ReopenedRemediationOutcomeModel).where(ReopenedRemediationOutcomeModel.tenant_id == self.tenant_id)
        if key:
            q = q.where(ReopenedRemediationOutcomeModel.deficiency_key == key)
        return list(self.session.scalars(q.order_by(ReopenedRemediationOutcomeModel.created_at.desc())))

    def outcome(self, outcome_id):
        return self.session.scalar(select(ReopenedRemediationOutcomeModel).where(ReopenedRemediationOutcomeModel.tenant_id == self.tenant_id, ReopenedRemediationOutcomeModel.outcome_id == outcome_id))

    def revalidations(self, key=None):
        q = select(ReopenedControlRevalidationModel).where(ReopenedControlRevalidationModel.tenant_id == self.tenant_id)
        if key:
            q = q.where(ReopenedControlRevalidationModel.deficiency_key == key)
        return list(self.session.scalars(q.order_by(ReopenedControlRevalidationModel.validated_at.desc().nullslast())))

    def assurances(self, key=None):
        q = select(RecurrenceClosureAssuranceModel).where(RecurrenceClosureAssuranceModel.tenant_id == self.tenant_id)
        if key:
            q = q.where(RecurrenceClosureAssuranceModel.deficiency_key == key)
        return list(self.session.scalars(q.order_by(RecurrenceClosureAssuranceModel.version)))

    def assurance(self, assurance_id):
        return self.session.scalar(select(RecurrenceClosureAssuranceModel).where(RecurrenceClosureAssuranceModel.tenant_id == self.tenant_id, RecurrenceClosureAssuranceModel.assurance_id == assurance_id))

    def recertifications(self, key=None):
        q = select(ReopenedIssueRecertificationModel).where(ReopenedIssueRecertificationModel.tenant_id == self.tenant_id)
        if key:
            q = q.where(ReopenedIssueRecertificationModel.deficiency_key == key)
        return list(self.session.scalars(q.order_by(ReopenedIssueRecertificationModel.decided_at.desc())))
