from __future__ import annotations
from datetime import datetime, timezone
from uuid import uuid4
from app.evaluation.regulatory_examination_reclosed_reauthorized_enterprise_remediation_surveillance import *

INDEPENDENT_ROLES = {"internal_auditor", "chief_audit_executive", "independent_assurance", "independent_validator"}
INVESTIGATION_ROLES = {"internal_auditor", "chief_audit_executive", "independent_assurance", "regulatory_affairs", "compliance_reviewer"}
CHALLENGE_ROLES = {"chief_risk_officer", "chief_compliance_officer", "executive_risk_committee", "chief_audit_executive", "executive_certifier"}
REOPEN_ROLES = {"chief_risk_officer", "chief_compliance_officer", "executive_risk_committee", "executive_certifier"}

class RegulatoryExaminationReclosedReauthorizedEnterpriseRemediationSurveillanceService:
    def __init__(self, db, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    def _now(self):
        return datetime.now(timezone.utc).isoformat()

    def _immutable(self, payload: dict):
        result = dict(payload)
        result["version_hash"] = version_hash(result)
        result["immutable"] = True
        return result

    def _release101(self, payload: dict):
        if not payload.get("release101_reauthorized_enterprise_remediation_sustainability_reclosure_version_id"):
            raise ValueError("Release 101 reauthorized enterprise remediation sustainability reclosure version is required")

    def decay(self, payload: dict):
        self._release101(payload)
        return {"tenant_id": self.tenant_id, "monitoring_only": True, **multi_cycle_enterprise_recovery_decay(payload)}

    def root_cause_treatment_decay(self, payload: dict):
        self._release101(payload)
        return {"tenant_id": self.tenant_id, "monitoring_only": True, **root_cause_treatment_decay(payload)}

    def control_regression(self, payload: dict):
        return {"tenant_id": self.tenant_id, "monitoring_only": True, **systemic_control_retransformation_regression(payload)}

    def rebound(self, payload: dict):
        return {"tenant_id": self.tenant_id, "monitoring_only": True, **systemic_risk_rebound(payload)}

    def recurrence(self, payload: dict):
        return {"tenant_id": self.tenant_id, "monitoring_only": True, **cross_entity_recurrence(payload)}

    def compare(self, payload: dict):
        return {"tenant_id": self.tenant_id, "analysis_only": True, **prior_enterprise_reclosure_comparison(payload)}

    def correlate_findings(self, payload: dict):
        return {"tenant_id": self.tenant_id, "analysis_only": True, **examination_finding_correlation(payload)}

    def regulator_followups(self, payload: dict):
        return {"tenant_id": self.tenant_id, "analysis_only": True, **regulator_followup_linkage(payload)}

    def materiality(self, payload: dict):
        return {"tenant_id": self.tenant_id, "analysis_only": True, **enterprise_materiality(payload)}

    def dashboard(self, payload: dict):
        self._release101(payload)
        return {"tenant_id": self.tenant_id, **supervisory_dashboard_summary(payload)}

    def audit_export(self, payload: dict):
        self._release101(payload)
        return {"tenant_id": self.tenant_id, **audit_export_manifest({**payload, "tenant_id": self.tenant_id})}

    def create_investigation(self, actor_id: str, payload: dict):
        if payload.get("actor_role") not in INVESTIGATION_ROLES:
            raise PermissionError("authorized human enterprise recovery investigator required")
        self._release101(payload)
        if not payload.get("surveillance_version_refs") or not payload.get("evidence_refs"):
            raise ValueError("surveillance and evidence references are required")
        if not payload.get("enterprise_materiality_version_ref"):
            raise ValueError("enterprise materiality reference is required for authoritative investigation")
        return self._immutable({
            "enterprise_recovery_decay_investigation_version_id": str(uuid4()),
            "tenant_id": self.tenant_id,
            "human_investigation": True,
            "automated_investigation_opening": False,
            "opened_by": actor_id,
            "opened_at": self._now(),
            **payload,
        })

    def independent_reassess(self, actor_id: str, payload: dict):
        if payload.get("actor_role") not in INDEPENDENT_ROLES:
            raise PermissionError("independent human enterprise recovery reassessor required")
        if not payload.get("investigation_version_id"):
            raise ValueError("human investigation reference required")
        if payload.get("investigation_owner_id") and str(payload.get("investigation_owner_id")) == str(actor_id):
            raise PermissionError("segregation of duties: investigation owner cannot perform independent reassessment")
        if not payload.get("evidence_refs"):
            raise ValueError("evidence-bound independent reassessment is required")
        return self._immutable({
            "enterprise_independent_reassessment_version_id": str(uuid4()),
            "tenant_id": self.tenant_id,
            "human_reassessment": True,
            "automated_reassessment": False,
            "reassessed_by": actor_id,
            "reassessed_at": self._now(),
            **payload,
        })

    def enterprise_challenge(self, actor_id: str, payload: dict):
        if payload.get("actor_role") not in CHALLENGE_ROLES:
            raise PermissionError("authorized executive/internal-audit human challenge required")
        if not payload.get("investigation_version_id") or not payload.get("independent_reassessment_version_id"):
            raise ValueError("investigation and independent reassessment references are required")
        if not payload.get("evidence_refs"):
            raise ValueError("evidence-bound executive/internal-audit challenge is required")
        return self._immutable({
            "enterprise_recovery_reopening_challenge_version_id": str(uuid4()),
            "tenant_id": self.tenant_id,
            "human_decision": True,
            "automated_reopening": False,
            "decided_by": actor_id,
            "decided_at": self._now(),
            **payload,
        })

    def readiness(self, payload: dict):
        return {"tenant_id": self.tenant_id, **enterprise_reopening_readiness(payload)}

    def decide_reopening(self, actor_id: str, payload: dict):
        if payload.get("actor_role") not in REOPEN_ROLES:
            raise PermissionError("authorized executive human enterprise reopening decision required")
        self._release101(payload)
        required = ["investigation_version_id", "independent_reassessment_version_id", "enterprise_challenge_version_id"]
        if any(not payload.get(key) for key in required):
            raise ValueError("investigation, independent reassessment and enterprise challenge references are required")
        if payload.get("decision") == "reopen":
            readiness = enterprise_reopening_readiness(payload.get("readiness", {}))
            if not readiness["ready_for_human_enterprise_reopening"]:
                raise ValueError("enterprise reopening gates are incomplete")
        return self._immutable({
            "enterprise_recovery_reopening_version_id": str(uuid4()),
            "tenant_id": self.tenant_id,
            "human_reopening": True,
            "automated_reopening": False,
            "decided_by": actor_id,
            "decided_at": self._now(),
            **payload,
        })
