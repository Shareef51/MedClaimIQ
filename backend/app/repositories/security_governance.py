from __future__ import annotations
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.claims import AuditEventModel
from app.models.security_governance import DataRetentionPolicyModel,DataDispositionRequestModel,AuditExportManifestModel,SecurityReadinessRunModel,EncryptionKeyReferenceModel

class SecurityGovernanceRepository:
    def __init__(self,session:Session,tenant_id:str): self.session=session; self.tenant_id=tenant_id
    def add(self,row): self.session.add(row); self.session.flush(); return row
    def active_retention_policies(self): return list(self.session.scalars(select(DataRetentionPolicyModel).where(DataRetentionPolicyModel.tenant_id==self.tenant_id,DataRetentionPolicyModel.active.is_(True))))
    def audit_events(self,from_time:datetime,to_time:datetime): return list(self.session.scalars(select(AuditEventModel).where(AuditEventModel.tenant_id==self.tenant_id,AuditEventModel.occurred_at>=from_time,AuditEventModel.occurred_at<=to_time).order_by(AuditEventModel.occurred_at,AuditEventModel.audit_event_id)))
    def readiness_runs(self,limit:int=20): return list(self.session.scalars(select(SecurityReadinessRunModel).where(SecurityReadinessRunModel.tenant_id==self.tenant_id).order_by(SecurityReadinessRunModel.run_at.desc()).limit(limit)))
    def key_references(self): return list(self.session.scalars(select(EncryptionKeyReferenceModel).where(EncryptionKeyReferenceModel.tenant_id==self.tenant_id).order_by(EncryptionKeyReferenceModel.activated_at.desc())))
