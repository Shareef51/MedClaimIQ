from __future__ import annotations
import hashlib,json
from datetime import datetime,timezone,timedelta
from pathlib import Path
from uuid import uuid4
from app.models.security_governance import DataRetentionPolicyModel,DataDispositionRequestModel,AuditExportManifestModel,SecurityReadinessRunModel,EncryptionKeyReferenceModel
from app.repositories.security_governance import SecurityGovernanceRepository
from app.security.audit_integrity import build_hash_chain
from app.security.data_classification import DLPRedactor

ROOT=Path(__file__).resolve().parents[3]

def load_security_policy(): return json.loads((ROOT/"config/security_privacy_policy.json").read_text())
def security_model_contract(settings):
    policy=load_security_policy()
    return {"compliance_posture":"HIPAA-ready technical architecture; not a legal compliance certification","classification_levels":policy["classification_levels"],"dlp":{"raw_phi_in_operational_logs":False,"secret_redaction":True},"key_management":{"production":"external KMS/secret manager","plaintext_data_keys_persisted":False},"retention":{"destructive_execution_requires_approval":True},"security_gate":policy["security_gate"],"control_baselines":["HIPAA Security Rule (currently effective)","NIST SP 800-66 Rev.2","OWASP ASVS 5.0","SLSA provenance principles","CycloneDX SBOM"]}

class SecurityGovernanceService:
    def __init__(self,repo:SecurityGovernanceRepository,settings,object_storage=None): self.repo=repo; self.settings=settings; self.policy=load_security_policy(); self.object_storage=object_storage
    def create_retention_policy(self,payload,actor_id):
        row=DataRetentionPolicyModel(policy_id=f"ret_{uuid4().hex}",tenant_id=self.repo.tenant_id,policy_key=payload.policy_key,version=payload.version,resource_type=payload.resource_type,classification=payload.classification,retention_days=payload.retention_days,disposition=payload.disposition,active=False,effective_from=datetime.now(timezone.utc),created_by=actor_id); return self.repo.add(row)
    def request_disposition(self,payload,actor_id):
        row=DataDispositionRequestModel(request_id=f"disp_{uuid4().hex}",tenant_id=self.repo.tenant_id,policy_id=payload.policy_id,resource_type=payload.resource_type,resource_id=payload.resource_id,classification=payload.classification,requested_by=actor_id,status="dry_run" if payload.dry_run else "pending_approval",dry_run=payload.dry_run,idempotency_key=payload.idempotency_key,reason=payload.reason); return self.repo.add(row)
    def export_audit(self,payload,actor_id):
        if payload.to_time <= payload.from_time: raise ValueError("to_time must be after from_time")
        events=self.repo.audit_events(payload.from_time,payload.to_time)
        redactor=DLPRedactor(); records=[]
        for e in events:
            safe,_=redactor.redact({"audit_event_id":e.audit_event_id,"actor_type":e.actor_type,"actor_id":e.actor_id,"action":e.action,"resource_type":e.resource_type,"resource_id":e.resource_id,"trace_id":e.trace_id,"details":e.details,"occurred_at":e.occurred_at.isoformat()})
            records.append(safe)
        secret=self.settings.security_audit_export_hmac_secret.get_secret_value().encode()
        export=build_hash_chain(records,signing_secret=secret)
        export_id=f"aexp_{uuid4().hex}"
        body=("\n".join(export.lines)+("\n" if export.lines else "")).encode("utf-8")
        object_key=f"audit-exports/{self.repo.tenant_id}/{export_id}.jsonl"
        path=None
        if self.object_storage is not None:
            self.object_storage.put_object(bucket=self.settings.s3_bucket,key=object_key,body=body,content_type="application/x-ndjson",metadata={"root-sha256":export.root_sha256,"classification":"confidential"})
        else:
            artifact_dir=ROOT/"artifacts/security/audit-exports"; artifact_dir.mkdir(parents=True,exist_ok=True); path=artifact_dir/f"{export_id}.jsonl"; path.write_bytes(body); object_key=str(path.relative_to(ROOT))
        row=AuditExportManifestModel(export_id=export_id,tenant_id=self.repo.tenant_id,requested_by=actor_id,from_time=payload.from_time,to_time=payload.to_time,record_count=export.record_count,root_sha256=export.root_sha256,signature_hmac_sha256=export.signature_hmac_sha256,export_object_key=object_key,classification="confidential",expires_at=datetime.now(timezone.utc)+timedelta(days=7)); self.repo.add(row); return row,path
    def readiness_history(self): return self.repo.readiness_runs()
    def register_key_reference(self,payload):
        now=datetime.now(timezone.utc); row=EncryptionKeyReferenceModel(key_ref_id=f"keyref_{uuid4().hex}",tenant_id=self.repo.tenant_id,provider=payload.provider,purpose=payload.purpose,external_key_id=payload.external_key_id,status="active",activated_at=now,rotate_after=now+timedelta(days=payload.rotation_days)); return self.repo.add(row)
    def key_references(self):
        now=datetime.now(timezone.utc); return [{"key_ref_id":x.key_ref_id,"provider":x.provider,"purpose":x.purpose,"external_key_id":x.external_key_id,"status":x.status,"activated_at":x.activated_at,"rotate_after":x.rotate_after,"rotation_due":x.status=="active" and x.rotate_after<=now} for x in self.repo.key_references()]
