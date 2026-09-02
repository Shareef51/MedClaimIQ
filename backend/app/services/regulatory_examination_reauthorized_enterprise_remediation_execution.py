from __future__ import annotations
from datetime import datetime, timezone
from uuid import uuid4
from app.evaluation.regulatory_examination_reauthorized_enterprise_remediation_execution import *

EXECUTIVE_ROLES={"chief_risk_officer","chief_compliance_officer","executive_risk_committee","executive_certifier"}
INDEPENDENT_ROLES={"internal_auditor","chief_audit_executive","independent_assurance","independent_validator"}
EXECUTION_ROLES=EXECUTIVE_ROLES|{"recovery_governance","remediation_governance","regulatory_affairs","control_owner","enterprise_control_governance"}
CONTROL_APPROVER_ROLES=EXECUTIVE_ROLES|{"enterprise_control_governance","remediation_governance"}

class RegulatoryExaminationReauthorizedEnterpriseRemediationExecutionService:
    def __init__(self,db,tenant_id:str): self.db=db; self.tenant_id=tenant_id
    def _now(self): return datetime.now(timezone.utc).isoformat()
    def _immutable(self,p):
        r=dict(p); r["version_hash"]=version_hash(r); r["immutable"]=True; return r
    def create_program(self,actor_id,p):
        if p.get("actor_role") not in EXECUTION_ROLES: raise PermissionError("authorized human enterprise remediation-governance role required")
        required=["enterprise_remediation_reauthorization_version_id","release99_investigation_version_id","release99_investigation_conclusion_version_id","release99_root_cause_confirmation_version_id","release99_systemic_failure_classification_version_id","release99_strategy_candidate_version_id","release99_independent_challenge_version_id"]
        if any(not p.get(k) for k in required): raise ValueError("complete Release 99 enterprise remediation reauthorization provenance is required")
        if p.get("release99_human_reauthorization_confirmed") is not True or p.get("release99_reauthorization_decision")!="authorize": raise ValueError("confirmed Release 99 human enterprise remediation authorization is required")
        if not p.get("evidence_refs"): raise ValueError("evidence-bound Release 99 reauthorization provenance is required")
        return self._immutable({"enterprise_remediation_execution_version_id":str(uuid4()),"tenant_id":self.tenant_id,"release99_human_reauthorization_reference_required":True,"human_program_intake":True,"automated_program_approval":False,"created_by":actor_id,"created_at":self._now(),**p})
    def progress(self,p): return {"tenant_id":self.tenant_id,"analysis_only":True,**remediation_program_progress(p)}
    def root_cause_treatments(self,p): return {"tenant_id":self.tenant_id,"recommendation_only":True,**root_cause_treatment_mapping(p)}
    def control_retransformation(self,p): return {"tenant_id":self.tenant_id,"recommendation_only":True,**systemic_control_retransformation_status(p)}
    def deployment_sequence(self,p): return {"tenant_id":self.tenant_id,"analysis_only":True,**cross_entity_deployment_sequence(p)}
    def commitment_alignment(self,p): return {"tenant_id":self.tenant_id,"analysis_only":True,**regulatory_commitment_alignment(p)}
    def critical_path(self,p): return {"tenant_id":self.tenant_id,"analysis_only":True,**dependency_critical_path_assessment(p)}
    def detect_drift(self,p): return {"tenant_id":self.tenant_id,"analysis_only":True,**implementation_drift_detection(p)}
    def kpis(self,p): return {"tenant_id":self.tenant_id,"analysis_only":True,**systemic_recovery_kpi_assessment(p)}
    def enterprise_validation(self,p): return {"tenant_id":self.tenant_id,"analysis_only":True,**enterprise_wide_control_validation(p)}
    def blocker_escalation(self,p): return {"tenant_id":self.tenant_id,"recommendation_only":True,**blocker_escalation_assessment(p)}
    def readiness(self,p): return {"tenant_id":self.tenant_id,**execution_readiness(p)}
    def dashboard(self,p): return {"tenant_id":self.tenant_id,**supervisory_dashboard_summary(p)}
    def audit_export(self,p): return {"tenant_id":self.tenant_id,**audit_export_manifest({**p,"tenant_id":self.tenant_id})}
    def approve_control_retransformation(self,actor_id,p):
        if p.get("actor_role") not in CONTROL_APPROVER_ROLES: raise PermissionError("authorized human enterprise control approval role required")
        if not p.get("enterprise_remediation_execution_version_id") or not p.get("control_ids"): raise ValueError("enterprise remediation execution and control references required")
        if not p.get("release99_reauthorization_scope_references") or not p.get("root_cause_treatment_references") or not p.get("evidence_refs"): raise ValueError("Release 99 scope, root-cause treatment and evidence references required")
        return self._immutable({"enterprise_control_retransformation_approval_version_id":str(uuid4()),"tenant_id":self.tenant_id,"human_decision":True,"automated_decision":False,"approved_by":actor_id,"approved_at":self._now(),**p})
    def create_checkpoint(self,actor_id,p):
        if p.get("actor_role") not in EXECUTION_ROLES: raise PermissionError("authorized human enterprise remediation execution role required")
        if not p.get("enterprise_remediation_execution_version_id") or not p.get("evidence_refs"): raise ValueError("enterprise remediation execution version and evidence are required")
        return self._immutable({"enterprise_remediation_execution_checkpoint_version_id":str(uuid4()),"tenant_id":self.tenant_id,"human_checkpoint":True,"automated_completion_certification":False,"recorded_by":actor_id,"recorded_at":self._now(),**p})
    def independent_assurance(self,actor_id,p):
        if p.get("reviewer_role") not in INDEPENDENT_ROLES: raise PermissionError("independent human recovery-effectiveness reviewer required")
        if not p.get("enterprise_remediation_execution_version_id") or not p.get("tests") or not p.get("evidence_refs"): raise ValueError("execution version, tests and evidence references are required")
        if p.get("implementation_owner_id") and str(p.get("implementation_owner_id"))==str(actor_id): raise PermissionError("segregation of duties: implementation owner cannot perform independent assurance")
        ev=independent_recovery_effectiveness_assurance(p)
        return self._immutable({"enterprise_independent_recovery_effectiveness_assurance_version_id":str(uuid4()),"tenant_id":self.tenant_id,"human_reviewer":True,"automated_certification":False,"reviewed_by":actor_id,"reviewed_at":self._now(),"evaluation":ev,**p})
    def executive_review(self,actor_id,p):
        if p.get("actor_role") not in EXECUTIVE_ROLES: raise PermissionError("authorized executive human supervisory review required")
        if not p.get("enterprise_remediation_execution_version_id"): raise ValueError("enterprise remediation execution version is required")
        return self._immutable({"enterprise_remediation_executive_supervisory_review_version_id":str(uuid4()),"tenant_id":self.tenant_id,"human_decision":True,"automated_decision":False,"decided_by":actor_id,"decided_at":self._now(),**p})
