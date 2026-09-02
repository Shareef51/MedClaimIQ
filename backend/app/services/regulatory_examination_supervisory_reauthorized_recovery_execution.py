from __future__ import annotations
from datetime import datetime, timezone
from uuid import uuid4
from app.evaluation.regulatory_examination_supervisory_reauthorized_recovery_execution import *

EXECUTIVE_ROLES = {"chief_risk_officer", "chief_compliance_officer", "executive_risk_committee", "executive_certifier"}
INDEPENDENT_ROLES = {"internal_auditor", "chief_audit_executive", "independent_assurance", "independent_validator"}
EXECUTION_ROLES = EXECUTIVE_ROLES | INDEPENDENT_ROLES | {"recovery_governance", "remediation_governance", "regulatory_affairs", "control_owner"}

class RegulatoryExaminationSupervisoryReauthorizedRecoveryExecutionService:
    def __init__(self, db, tenant_id: str): self.db = db; self.tenant_id = tenant_id
    def _now(self): return datetime.now(timezone.utc).isoformat()
    def _immutable(self, payload: dict): payload["version_hash"] = version_hash(payload); return payload

    def create_program(self, actor_id: str, p: dict):
        if p.get("actor_role") not in EXECUTION_ROLES:
            raise PermissionError("authorized human supervisory recovery-governance role required")
        if not p.get("supervisory_recovery_reauthorization_version_id"):
            raise ValueError("Release 91 human supervisory recovery reauthorization version is required")
        if not p.get("release91_investigation_version_id"):
            raise ValueError("Release 91 reopened recovery investigation version is required")
        return self._immutable({
            "supervisory_reauthorized_recovery_execution_version_id": str(uuid4()),
            "tenant_id": self.tenant_id,
            "release91_human_reauthorization_reference_required": True,
            "automated_program_approval": False,
            "created_by": actor_id,
            "created_at": self._now(),
            **p,
        })

    def progress(self, p: dict): return {"tenant_id": self.tenant_id, "analysis_only": True, **supervisory_program_progress(p)}
    def control_retransformation(self, p: dict): return {"tenant_id": self.tenant_id, "recommendation_only": True, **control_retransformation_status(p)}
    def deployment_sequence(self, p: dict): return {"tenant_id": self.tenant_id, "analysis_only": True, **deployment_sequence_assessment(p)}
    def critical_path(self, p: dict): return {"tenant_id": self.tenant_id, "analysis_only": True, **critical_path_assessment(p)}
    def detect_drift(self, p: dict): return {"tenant_id": self.tenant_id, "analysis_only": True, **implementation_drift(p)}
    def kpis(self, p: dict): return {"tenant_id": self.tenant_id, "analysis_only": True, **recovery_kpi_assessment(p)}

    def create_checkpoint(self, actor_id: str, p: dict):
        if p.get("actor_role") not in EXECUTION_ROLES:
            raise PermissionError("authorized human recovery execution role required")
        if not p.get("supervisory_recovery_execution_version_id"):
            raise ValueError("supervisory recovery execution version is required")
        if not p.get("evidence_refs"):
            raise ValueError("evidence-bound execution checkpoint requires evidence references")
        return self._immutable({
            "supervisory_recovery_execution_checkpoint_version_id": str(uuid4()),
            "tenant_id": self.tenant_id,
            "human_checkpoint": True,
            "automated_completion_certification": False,
            "recorded_by": actor_id,
            "recorded_at": self._now(),
            **p,
        })

    def independent_assurance(self, actor_id: str, p: dict):
        if p.get("reviewer_role") not in INDEPENDENT_ROLES:
            raise PermissionError("independent human reviewer required")
        if not p.get("supervisory_recovery_execution_version_id"):
            raise ValueError("supervisory recovery execution version is required")
        result = independent_recovery_assurance(p)
        return self._immutable({
            "supervisory_independent_recovery_assurance_version_id": str(uuid4()),
            "tenant_id": self.tenant_id,
            "human_reviewer": True,
            "automated_certification": False,
            "reviewed_by": actor_id,
            "reviewed_at": self._now(),
            "evaluation": result,
            **p,
        })

    def readiness(self, p: dict): return {"tenant_id": self.tenant_id, **execution_readiness(p)}

    def executive_review(self, actor_id: str, p: dict):
        if p.get("actor_role") not in EXECUTIVE_ROLES:
            raise PermissionError("authorized executive human review required")
        if not p.get("supervisory_recovery_execution_version_id"):
            raise ValueError("supervisory recovery execution version is required")
        return self._immutable({
            "supervisory_recovery_executive_progress_review_version_id": str(uuid4()),
            "tenant_id": self.tenant_id,
            "human_decision": True,
            "automated_decision": False,
            "decided_by": actor_id,
            "decided_at": self._now(),
            **p,
        })
