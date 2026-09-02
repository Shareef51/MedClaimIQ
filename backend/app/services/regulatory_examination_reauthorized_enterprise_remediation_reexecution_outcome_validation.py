from __future__ import annotations
from datetime import datetime, timezone
from uuid import uuid4
from app.evaluation.regulatory_examination_reauthorized_enterprise_remediation_reexecution_outcome_validation import *

EXECUTIVE_ROLES = {"chief_risk_officer", "chief_compliance_officer", "executive_risk_committee", "executive_certifier"}
INDEPENDENT_ROLES = {"internal_auditor", "chief_audit_executive", "independent_assurance", "independent_validator"}

class RegulatoryExaminationReauthorizedEnterpriseRemediationReExecutionOutcomeValidationService:
    def __init__(self, db, tenant_id: str): self.db = db; self.tenant_id = tenant_id
    def _now(self): return datetime.now(timezone.utc).isoformat()
    def _immutable(self, payload: dict):
        result = dict(payload); result["version_hash"] = version_hash(result); result["immutable"] = True; return result

    def outcomes(self, p: dict):
        if not p.get("release104_enterprise_remediation_reexecution_version_id"):
            raise ValueError("Release 104 enterprise remediation re-execution version is required")
        return {"tenant_id": self.tenant_id, "analysis_only": True, **enterprise_recovery_outcomes(p)}

    def root_cause_treatments(self, p: dict): return {"tenant_id": self.tenant_id, "analysis_only": True, **root_cause_treatment_effectiveness(p)}

    def risk_reduction(self, p: dict): return {"tenant_id": self.tenant_id, "analysis_only": True, **systemic_risk_reduction(p)}
    def control_completion(self, p: dict): return {"tenant_id": self.tenant_id, "analysis_only": True, **enterprise_control_completion(p)}
    def repeated_failure_effectiveness(self, p: dict): return {"tenant_id": self.tenant_id, "analysis_only": True, **repeated_failure_control_effectiveness(p)}
    def commitments(self, p: dict): return {"tenant_id": self.tenant_id, "analysis_only": True, **regulatory_commitment_completion(p)}
    def blockers(self, p: dict): return {"tenant_id": self.tenant_id, "monitoring_only": True, **blocker_governance(p)}
    def control_health(self, p: dict): return {"tenant_id": self.tenant_id, "monitoring_only": True, **cross_entity_control_health(p)}

    def independent_validate(self, actor_id: str, p: dict):
        if p.get("reviewer_role") not in INDEPENDENT_ROLES:
            raise PermissionError("independent human enterprise recovery outcome reviewer required")
        if not p.get("release104_enterprise_remediation_reexecution_version_id") or not p.get("release104_independent_recovery_effectiveness_assurance_version_id"):
            raise ValueError("Release 104 enterprise remediation re-execution and independent recovery-effectiveness assurance references are required")
        if p.get("implementation_owner_id") and str(p.get("implementation_owner_id")) == str(actor_id):
            raise PermissionError("segregation of duties: implementation owner cannot perform independent outcome assurance")
        result = independent_enterprise_outcome_assurance(p)
        return self._immutable({
            "reauthorized_enterprise_remediation_reexecution_independent_outcome_validation_version_id": str(uuid4()),
            "tenant_id": self.tenant_id,
            "human_reviewer": True,
            "automated_certification": False,
            "reviewed_by": actor_id,
            "reviewed_at": self._now(),
            "evaluation": result,
            **p,
        })

    def sustainability(self, p: dict):
        if not p.get("recovery_program_id"):
            raise ValueError("recovery program is required")
        return self._immutable({
            "reauthorized_enterprise_remediation_reexecution_sustainability_assessment_version_id": str(uuid4()),
            "tenant_id": self.tenant_id,
            "analysis_only": True,
            "automated_reclosure": False,
            "assessed_at": self._now(),
            "evaluation": sustainability_assessment(p),
            **p,
        })

    def readiness(self, p: dict): return {"tenant_id": self.tenant_id, **reclosure_readiness(p)}
    def dashboard(self, p: dict): return {"tenant_id": self.tenant_id, **supervisory_dashboard_summary(p)}
    def audit_export(self, p: dict): return {"tenant_id": self.tenant_id, **audit_export_manifest({**p, "tenant_id": self.tenant_id})}

    def residual_risk_reassessment(self, actor_id: str, p: dict):
        if p.get("actor_role") not in EXECUTIVE_ROLES:
            raise PermissionError("authorized executive human residual-systemic-risk reassessment required")
        if p.get("decision") not in {"accept", "reject", "request_more_evidence"}:
            raise ValueError("invalid residual-risk reassessment decision")
        required = [
            "release104_enterprise_remediation_reexecution_version_id",
            "release104_independent_recovery_effectiveness_assurance_version_id",
            "independent_outcome_validation_version_id",
            "sustainability_assessment_version_id",
        ]
        if any(not p.get(k) for k in required):
            raise ValueError("Release 104 remediation re-execution/recovery-effectiveness assurance, independent outcome validation and sustainability references are required")
        if not p.get("evidence_refs"):
            raise ValueError("evidence-bound residual-risk reassessment is required")
        return self._immutable({
            "reauthorized_enterprise_remediation_reexecution_residual_risk_decision_version_id": str(uuid4()),
            "tenant_id": self.tenant_id,
            "human_decision": True,
            "automated_risk_acceptance": False,
            "decided_by": actor_id,
            "decided_at": self._now(),
            **p,
        })

    def recertify_recovery(self, actor_id: str, p: dict):
        if p.get("actor_role") not in EXECUTIVE_ROLES:
            raise PermissionError("authorized executive human systemic recovery recertification required")
        if p.get("decision") not in {"recertify", "withhold", "request_more_evidence"}:
            raise ValueError("invalid recovery recertification decision")
        required = [
            "release104_enterprise_remediation_reexecution_version_id",
            "release104_independent_recovery_effectiveness_assurance_version_id",
            "independent_outcome_validation_version_id",
            "residual_risk_decision_version_id",
            "sustainability_assessment_version_id",
        ]
        if any(not p.get(k) for k in required):
            raise ValueError("Release 104 remediation re-execution/recovery-effectiveness assurance, independent outcome validation, residual-risk and sustainability references are required")
        if p.get("decision") == "recertify" and p.get("residual_risk_decision") != "accept":
            raise ValueError("recovery recertification requires explicit human residual-risk acceptance")
        if p.get("decision") == "recertify" and p.get("reclosure_readiness_confirmed") is not True:
            raise ValueError("deterministic sustainability reclosure readiness must be confirmed before recertification")
        return self._immutable({
            "reauthorized_enterprise_remediation_reexecution_systemic_recovery_recertification_version_id": str(uuid4()),
            "tenant_id": self.tenant_id,
            "human_decision": True,
            "automated_recertification": False,
            "decided_by": actor_id,
            "decided_at": self._now(),
            **p,
        })

    def reclose_program(self, actor_id: str, p: dict):
        if p.get("actor_role") not in EXECUTIVE_ROLES:
            raise PermissionError("authorized executive human sustainability reclosure required")
        if p.get("decision") not in {"reclose", "withhold", "request_more_evidence"}:
            raise ValueError("invalid sustainability reclosure decision")
        if not p.get("reauthorized_enterprise_remediation_reexecution_systemic_recovery_recertification_version_id"):
            raise ValueError("human executive systemic recovery recertification reference is required")
        if p.get("decision") == "reclose" and p.get("sustainability_assurance_passed") is not True:
            raise ValueError("sustainability assurance must pass before program reclosure")
        return self._immutable({
            "reauthorized_enterprise_remediation_reexecution_sustainability_reclosure_version_id": str(uuid4()),
            "tenant_id": self.tenant_id,
            "human_decision": True,
            "automated_reclosure": False,
            "decided_by": actor_id,
            "decided_at": self._now(),
            **p,
        })
