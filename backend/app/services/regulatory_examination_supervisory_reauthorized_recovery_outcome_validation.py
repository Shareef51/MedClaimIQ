from __future__ import annotations
from datetime import datetime, timezone
from uuid import uuid4
from app.evaluation.regulatory_examination_supervisory_reauthorized_recovery_outcome_validation import *

EXECUTIVE_ROLES = {"chief_risk_officer", "chief_compliance_officer", "executive_risk_committee", "executive_certifier"}
INDEPENDENT_ROLES = {"internal_auditor", "chief_audit_executive", "independent_assurance", "independent_validator"}

class RegulatoryExaminationSupervisoryReauthorizedRecoveryOutcomeValidationService:
    def __init__(self, db, tenant_id: str): self.db = db; self.tenant_id = tenant_id
    def _now(self): return datetime.now(timezone.utc).isoformat()
    def _immutable(self, payload: dict): payload["version_hash"] = version_hash(payload); return payload

    def outcomes(self, p: dict):
        if not p.get("release92_supervisory_recovery_execution_version_id"):
            raise ValueError("Release 92 supervisory recovery execution version is required")
        return {"tenant_id": self.tenant_id, "analysis_only": True, **supervisory_recovery_outcomes(p)}

    def risk_reduction(self, p: dict): return {"tenant_id": self.tenant_id, "analysis_only": True, **systemic_risk_reduction(p)}
    def entity_completion(self, p: dict): return {"tenant_id": self.tenant_id, "analysis_only": True, **cross_entity_retransformation_completion(p)}
    def repeated_failure_effectiveness(self, p: dict): return {"tenant_id": self.tenant_id, "analysis_only": True, **repeated_failure_control_effectiveness(p)}
    def commitments(self, p: dict): return {"tenant_id": self.tenant_id, "analysis_only": True, **regulatory_commitment_completion(p)}
    def blockers(self, p: dict): return {"tenant_id": self.tenant_id, "monitoring_only": True, **blocker_governance(p)}

    def independent_validate(self, actor_id: str, p: dict):
        if p.get("reviewer_role") not in INDEPENDENT_ROLES:
            raise PermissionError("independent human supervisory recovery outcome reviewer required")
        if not p.get("release92_supervisory_recovery_execution_version_id") or not p.get("release92_independent_recovery_assurance_version_id"):
            raise ValueError("Release 92 execution and independent assurance references are required")
        result = independent_recovery_outcome_assurance(p)
        return self._immutable({
            "supervisory_independent_outcome_validation_version_id": str(uuid4()),
            "tenant_id": self.tenant_id,
            "human_reviewer": True,
            "automated_certification": False,
            "reviewed_by": actor_id,
            "reviewed_at": self._now(),
            "evaluation": result,
            **p,
        })

    def sustainability(self, p: dict):
        return self._immutable({
            "supervisory_sustainability_assessment_version_id": str(uuid4()),
            "tenant_id": self.tenant_id,
            "analysis_only": True,
            "automated_reclosure": False,
            "assessed_at": self._now(),
            "evaluation": sustainability_assessment(p),
            **p,
        })

    def readiness(self, p: dict): return {"tenant_id": self.tenant_id, **reclosure_readiness(p)}

    def residual_risk_reassessment(self, actor_id: str, p: dict):
        if p.get("actor_role") not in EXECUTIVE_ROLES:
            raise PermissionError("authorized executive human residual-risk reassessment required")
        if p.get("decision") not in {"accept", "reject", "request_more_evidence"}:
            raise ValueError("invalid residual-risk reassessment decision")
        if not p.get("release92_supervisory_recovery_execution_version_id"):
            raise ValueError("Release 92 supervisory recovery execution reference is required")
        return self._immutable({
            "supervisory_residual_risk_decision_version_id": str(uuid4()),
            "tenant_id": self.tenant_id,
            "human_decision": True,
            "automated_risk_acceptance": False,
            "decided_by": actor_id,
            "decided_at": self._now(),
            **p,
        })

    def recertify_recovery(self, actor_id: str, p: dict):
        if p.get("actor_role") not in EXECUTIVE_ROLES:
            raise PermissionError("authorized executive human recovery recertification required")
        if p.get("decision") not in {"recertify", "withhold", "request_more_evidence"}:
            raise ValueError("invalid recovery recertification decision")
        required = [
            "release92_supervisory_recovery_execution_version_id",
            "release92_independent_recovery_assurance_version_id",
            "independent_outcome_validation_version_id",
            "residual_risk_decision_version_id",
            "sustainability_assessment_version_id",
        ]
        if any(not p.get(k) for k in required):
            raise ValueError("Release 92 execution/assurance, independent outcome validation, residual-risk and sustainability references are required")
        return self._immutable({
            "supervisory_recovery_recertification_version_id": str(uuid4()),
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
        if not p.get("recovery_recertification_version_id"):
            raise ValueError("human executive recovery recertification reference is required")
        return self._immutable({
            "supervisory_sustainability_reclosure_version_id": str(uuid4()),
            "tenant_id": self.tenant_id,
            "human_decision": True,
            "automated_reclosure": False,
            "decided_by": actor_id,
            "decided_at": self._now(),
            **p,
        })
