from __future__ import annotations
from fastapi import APIRouter,Depends,HTTPException,Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.domain.access import UserRole
from app.repositories.security_governance import SecurityGovernanceRepository
from app.schemas.security_governance import RetentionPolicyCreate,DispositionRequestCreate,AuditExportRequest,KeyReferenceCreate
from app.services.security_governance import SecurityGovernanceService,security_model_contract
from app.core.config import get_settings
router=APIRouter(tags=["security-governance"])
def ident(r):
    i=getattr(r.state,"identity",None)
    if not i: raise HTTPException(401,"authenticated identity required")
    return i
def require(i,write=False):
    allowed={UserRole.TENANT_ADMIN} if write else {UserRole.TENANT_ADMIN,UserRole.AUDITOR}
    if i.principal.role not in allowed: raise HTTPException(403,"security governance access denied")
@router.get("/security-model")
def model(): return security_model_contract(get_settings())
@router.get("/security/readiness")
def readiness(request:Request,db:Session=Depends(get_db)):
    i=ident(request);require(i); rows=SecurityGovernanceService(SecurityGovernanceRepository(db,i.principal.tenant_id),get_settings()).readiness_history(); return {"runs":[{"run_id":x.run_id,"candidate_version":x.candidate_version,"decision":x.decision,"critical_findings":x.critical_findings,"high_findings":x.high_findings,"control_pass_rate":x.control_pass_rate,"run_at":x.run_at} for x in rows]}
@router.post("/security/retention-policies")
def create_retention(payload:RetentionPolicyCreate,request:Request,db:Session=Depends(get_db)):
    i=ident(request);require(i,True); row=SecurityGovernanceService(SecurityGovernanceRepository(db,i.principal.tenant_id),get_settings()).create_retention_policy(payload,i.principal.user_id); db.commit(); return {"policy_id":row.policy_id,"active":row.active}
@router.post("/security/disposition-requests")
def disposition(payload:DispositionRequestCreate,request:Request,db:Session=Depends(get_db)):
    i=ident(request);require(i,True); row=SecurityGovernanceService(SecurityGovernanceRepository(db,i.principal.tenant_id),get_settings()).request_disposition(payload,i.principal.user_id); db.commit(); return {"request_id":row.request_id,"status":row.status,"dry_run":row.dry_run}
@router.post("/security/audit-exports")
def audit_export(payload:AuditExportRequest,request:Request,db:Session=Depends(get_db)):
    i=ident(request);require(i); provider=getattr(request.app.state,"object_storage_provider",None); storage=provider() if provider else None; service=SecurityGovernanceService(SecurityGovernanceRepository(db,i.principal.tenant_id),get_settings(),storage)
    try: row,path=service.export_audit(payload,i.principal.user_id)
    except ValueError as exc: raise HTTPException(400,str(exc)) from exc
    db.commit(); return {"export_id":row.export_id,"record_count":row.record_count,"root_sha256":row.root_sha256,"signature_hmac_sha256":row.signature_hmac_sha256,"expires_at":row.expires_at,"object_key":row.export_object_key}


@router.get("/security/key-references")
def key_references(request:Request,db:Session=Depends(get_db)):
    i=ident(request);require(i); return {"keys":SecurityGovernanceService(SecurityGovernanceRepository(db,i.principal.tenant_id),get_settings()).key_references()}

@router.post("/security/key-references")
def register_key_reference(payload:KeyReferenceCreate,request:Request,db:Session=Depends(get_db)):
    i=ident(request);require(i,True); row=SecurityGovernanceService(SecurityGovernanceRepository(db,i.principal.tenant_id),get_settings()).register_key_reference(payload); db.commit(); return {"key_ref_id":row.key_ref_id,"status":row.status,"rotate_after":row.rotate_after}
