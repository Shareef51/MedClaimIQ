from fastapi import APIRouter,Depends,HTTPException,Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.domain.production_security_privacy_compliance_red_team import production_security_privacy_compliance_red_team_contract
from app.schemas.production_security_privacy_compliance_red_team import *
from app.services.production_security_privacy_compliance_red_team import ProductionSecurityPrivacyComplianceRedTeamService
router=APIRouter(tags=["production-security-privacy-compliance-red-team"]); BASE="/release-security-certification"
def _identity(r):
    i=getattr(r.state,"identity",None)
    if i is None: raise HTTPException(401,"authenticated identity unavailable")
    return i
def _svc(db,i): return ProductionSecurityPrivacyComplianceRedTeamService(db,i.principal.tenant_id)
def _call(fn):
    try:return fn()
    except PermissionError as e: raise HTTPException(403,str(e)) from e
    except ValueError as e: raise HTTPException(422,str(e)) from e
@router.get(BASE+"/model")
def model(): return production_security_privacy_compliance_red_team_contract()
@router.post(BASE+"/cross-tenant")
def cross_tenant(p:CasesRequest,r:Request,db:Session=Depends(get_db)): return _call(lambda:_svc(db,_identity(r)).cross_tenant(p.model_dump()))
@router.post(BASE+"/authorization-abuse")
def authz(p:CasesRequest,r:Request,db:Session=Depends(get_db)): return _call(lambda:_svc(db,_identity(r)).authorization(p.model_dump()))
@router.post(BASE+"/prompt-injection")
def prompt(p:CasesRequest,r:Request,db:Session=Depends(get_db)): return _call(lambda:_svc(db,_identity(r)).prompt_injection(p.model_dump()))
@router.post(BASE+"/rag-poisoning-exfiltration")
def rag(p:CasesRequest,r:Request,db:Session=Depends(get_db)): return _call(lambda:_svc(db,_identity(r)).rag_abuse(p.model_dump()))
@router.post(BASE+"/mcp-tool-abuse")
def mcp(p:CasesRequest,r:Request,db:Session=Depends(get_db)): return _call(lambda:_svc(db,_identity(r)).mcp_abuse(p.model_dump()))
@router.post(BASE+"/agent-privilege-boundary")
def agent(p:CasesRequest,r:Request,db:Session=Depends(get_db)): return _call(lambda:_svc(db,_identity(r)).agent_boundary(p.model_dump()))
@router.post(BASE+"/phi-pii-leakage")
def leak(p:CasesRequest,r:Request,db:Session=Depends(get_db)): return _call(lambda:_svc(db,_identity(r)).leakage(p.model_dump()))
@router.post(BASE+"/supply-chain")
def supply(p:SupplyChainAssessmentRequest,r:Request,db:Session=Depends(get_db)): return _call(lambda:_svc(db,_identity(r)).supply_chain(p.model_dump()))
@router.post(BASE+"/api-fuzzing")
def fuzz(p:CasesRequest,r:Request,db:Session=Depends(get_db)): return _call(lambda:_svc(db,_identity(r)).api_fuzzing(p.model_dump()))
@router.post(BASE+"/audit-tamper")
def audit(p:CasesRequest,r:Request,db:Session=Depends(get_db)): return _call(lambda:_svc(db,_identity(r)).audit_tamper(p.model_dump()))
@router.post(BASE+"/adversarial-multimodal")
def multimodal(p:CasesRequest,r:Request,db:Session=Depends(get_db)): return _call(lambda:_svc(db,_identity(r)).multimodal(p.model_dump()))
@router.post(BASE+"/readiness")
def readiness(p:SecurityReleaseReadinessRequest,r:Request,db:Session=Depends(get_db)): return _call(lambda:_svc(db,_identity(r)).readiness(p.model_dump()))
@router.post(BASE+"/compliance-evidence-pack")
def pack(p:SecurityReleaseReadinessRequest,r:Request,db:Session=Depends(get_db)): return _call(lambda:_svc(db,_identity(r)).evidence_pack(p.model_dump()))
@router.post(BASE+"/red-team-runs")
def run(p:SecurityRedTeamRunCreate,r:Request,db:Session=Depends(get_db)):
    i=_identity(r); return _call(lambda:_svc(db,i).create_red_team_run(i.principal.user_id,p.model_dump()))
@router.post(BASE+"/waivers")
def waiver(p:SecurityWaiverCreate,r:Request,db:Session=Depends(get_db)):
    i=_identity(r); return _call(lambda:_svc(db,i).approve_waiver(i.principal.user_id,p.model_dump()))
@router.post(BASE+"/certifications")
def certify(p:SecurityCertificationCreate,r:Request,db:Session=Depends(get_db)):
    i=_identity(r); return _call(lambda:_svc(db,i).certify(i.principal.user_id,p.model_dump()))
