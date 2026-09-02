from __future__ import annotations
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.db.session import set_tenant_context
from app.models.recovery_control_assurance import *


class RecoveryControlAssuranceRepository:
    def __init__(self, session: Session, tenant_id: str):
        self.session=session; self.tenant_id=tenant_id; set_tenant_context(session,tenant_id)
    def add(self,row):
        if row.tenant_id!=self.tenant_id: raise ValueError("tenant mismatch")
        self.session.add(row); self.session.flush(); return row
    def period(self,period_id): return self.session.scalar(select(RegulatoryReportingPeriodModel).where(RegulatoryReportingPeriodModel.tenant_id==self.tenant_id,RegulatoryReportingPeriodModel.reporting_period_id==period_id))
    def period_by_key(self,key): return self.session.scalar(select(RegulatoryReportingPeriodModel).where(RegulatoryReportingPeriodModel.tenant_id==self.tenant_id,RegulatoryReportingPeriodModel.period_key==key))
    def periods(self): return list(self.session.scalars(select(RegulatoryReportingPeriodModel).where(RegulatoryReportingPeriodModel.tenant_id==self.tenant_id).order_by(RegulatoryReportingPeriodModel.end_date.desc())))
    def attestation_by_watermark(self,period_id,watermark): return self.session.scalar(select(PortfolioControlAttestationModel).where(PortfolioControlAttestationModel.tenant_id==self.tenant_id,PortfolioControlAttestationModel.reporting_period_id==period_id,PortfolioControlAttestationModel.source_watermark_sha256==watermark))
    def next_attestation_version(self,period_id): return int(self.session.scalar(select(func.max(PortfolioControlAttestationModel.attestation_version)).where(PortfolioControlAttestationModel.tenant_id==self.tenant_id,PortfolioControlAttestationModel.reporting_period_id==period_id)) or 0)+1
    def attestations(self,period_id): return list(self.session.scalars(select(PortfolioControlAttestationModel).where(PortfolioControlAttestationModel.tenant_id==self.tenant_id,PortfolioControlAttestationModel.reporting_period_id==period_id).order_by(PortfolioControlAttestationModel.attestation_version.desc())))
    def package(self,package_id,for_update=False):
        q=select(RegulatorySubmissionPackageModel).where(RegulatorySubmissionPackageModel.tenant_id==self.tenant_id,RegulatorySubmissionPackageModel.package_id==package_id)
        if for_update:q=q.with_for_update()
        return self.session.scalar(q)
    def package_by_idem(self,key): return self.session.scalar(select(RegulatorySubmissionPackageModel).where(RegulatorySubmissionPackageModel.tenant_id==self.tenant_id,RegulatorySubmissionPackageModel.idempotency_key==key))
    def packages(self,period_id=None):
        q=select(RegulatorySubmissionPackageModel).where(RegulatorySubmissionPackageModel.tenant_id==self.tenant_id)
        if period_id:q=q.where(RegulatorySubmissionPackageModel.reporting_period_id==period_id)
        return list(self.session.scalars(q.order_by(RegulatorySubmissionPackageModel.created_at.desc())))
    def next_package_version(self,period_id): return int(self.session.scalar(select(func.max(RegulatorySubmissionPackageModel.package_version)).where(RegulatorySubmissionPackageModel.tenant_id==self.tenant_id,RegulatorySubmissionPackageModel.reporting_period_id==period_id)) or 0)+1
    def samples(self,package_id): return list(self.session.scalars(select(ControlEvidenceSampleModel).where(ControlEvidenceSampleModel.tenant_id==self.tenant_id,ControlEvidenceSampleModel.package_id==package_id).order_by(ControlEvidenceSampleModel.sample_sequence)))
    def certification(self,package_id): return self.session.scalar(select(RegulatoryCertificationModel).where(RegulatoryCertificationModel.tenant_id==self.tenant_id,RegulatoryCertificationModel.package_id==package_id))
    def certifications(self,period_id): return list(self.session.scalars(select(RegulatoryCertificationModel).where(RegulatoryCertificationModel.tenant_id==self.tenant_id,RegulatoryCertificationModel.reporting_period_id==period_id).order_by(RegulatoryCertificationModel.certification_sequence)))
    def receipt(self,package_id): return self.session.scalar(select(RegulatorySubmissionReceiptModel).where(RegulatorySubmissionReceiptModel.tenant_id==self.tenant_id,RegulatorySubmissionReceiptModel.package_id==package_id))
    def annotations(self,package_id): return list(self.session.scalars(select(RegulatoryAuditAnnotationModel).where(RegulatoryAuditAnnotationModel.tenant_id==self.tenant_id,RegulatoryAuditAnnotationModel.package_id==package_id).order_by(RegulatoryAuditAnnotationModel.created_at)))
    def audit(self,period_id): return list(self.session.scalars(select(RegulatoryControlAuditEventModel).where(RegulatoryControlAuditEventModel.tenant_id==self.tenant_id,RegulatoryControlAuditEventModel.reporting_period_id==period_id).order_by(RegulatoryControlAuditEventModel.sequence)))
