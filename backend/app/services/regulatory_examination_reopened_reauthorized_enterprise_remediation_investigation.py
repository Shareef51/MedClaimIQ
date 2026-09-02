from __future__ import annotations
from datetime import datetime, timezone
from uuid import uuid4
from app.evaluation.regulatory_examination_reopened_reauthorized_enterprise_remediation_investigation import *

INVESTIGATOR_ROLES = {"internal_auditor", "chief_audit_executive", "independent_assurance", "regulatory_remediation_lead", "enterprise_recovery_investigator", "enterprise_remediation_investigator"}
INDEPENDENT_ROLES = {"internal_auditor", "chief_audit_executive", "independent_assurance", "independent_validator"}
EXECUTIVE_ROLES = {"chief_risk_officer", "chief_compliance_officer", "executive_risk_committee", "executive_certifier"}
CLASSIFICATION_ROLES = INVESTIGATOR_ROLES | EXECUTIVE_ROLES

class RegulatoryExaminationReopenedReauthorizedEnterpriseRemediationInvestigationService:
    def __init__(self, db, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    def _now(self): return datetime.now(timezone.utc).isoformat()
    def _immutable(self, payload: dict) -> dict:
        result = dict(payload)
        result["version_hash"] = version_hash(result)
        result["immutable"] = True
        return result

    def _release102(self, p: dict):
        if not p.get("release102_enterprise_recovery_reopening_version_id"):
            raise ValueError("Release 102 human enterprise reopening reference required")
        if p.get("release102_human_enterprise_reopening_verified") is not True:
            raise ValueError("Release 102 human enterprise reopening must be verified")

    def create_investigation(self, actor_id: str, p: dict):
        if p.get("actor_role") not in INVESTIGATOR_ROLES:
            raise PermissionError("authorized human enterprise remediation investigator required")
        self._release102(p)
        if not p.get("surveillance_version_refs") or not p.get("evidence_refs"):
            raise ValueError("Release 102 surveillance versions and evidence are required")
        return self._immutable({
            "reopened_reauthorized_enterprise_remediation_investigation_version_id": str(uuid4()),
            "tenant_id": self.tenant_id,
            "human_investigation": True,
            "automated_investigation": False,
            "opened_by": actor_id,
            "opened_at": self._now(),
            **p,
        })

    def reconstruct_evidence(self, p): return {"tenant_id": self.tenant_id, "analysis_only": True, **reconstruct_multi_cycle_remediation_evidence(p)}
    def analyze_treatment_failures(self, p): return {"tenant_id": self.tenant_id, "analysis_only": True, **analyze_persistent_emergent_treatment_failure(p)}
    def reconstruct_root_causes(self, p): return {"tenant_id": self.tenant_id, "recommendation_only": True, **reconstruct_systemic_remediation_failure_root_causes(p)}
    def validate_assumptions(self, p): return {"tenant_id": self.tenant_id, "analysis_only": True, **validate_prior_recertification_reclosure_assumptions(p)}
    def analyze_control_failures(self, p): return {"tenant_id": self.tenant_id, "recommendation_only": True, **analyze_repeated_systemic_control_retransformation_failures(p)}
    def causal_map(self, p): return {"tenant_id": self.tenant_id, "analysis_only": True, **map_cross_entity_causal_propagation(p)}
    def regulatory_impact(self, p): return {"tenant_id": self.tenant_id, "analysis_only": True, **assess_regulatory_commitment_followup_impact(p)}
    def classify_failure(self, p): return {"tenant_id": self.tenant_id, "proposal_only": True, **classify_systemic_remediation_failure(p)}
    def readiness(self, p): return {"tenant_id": self.tenant_id, **enterprise_remediation_reauthorization_readiness(p)}
    def dashboard(self, p): return {"tenant_id": self.tenant_id, **supervisory_dashboard_summary(p)}
    def audit_export(self, p): return {"tenant_id": self.tenant_id, **audit_export_manifest({**p, "tenant_id": self.tenant_id})}

    def confirm_root_causes(self, actor_id: str, p: dict):
        if p.get("actor_role") not in INVESTIGATOR_ROLES:
            raise PermissionError("authorized human remediation root-cause confirmation required")
        if not p.get("investigation_version_id") or not p.get("root_cause_analysis_version_id") or not p.get("evidence_refs"):
            raise ValueError("investigation, root-cause analysis and evidence references required")
        return self._immutable({
            "systemic_remediation_failure_root_cause_confirmation_version_id": str(uuid4()),
            "tenant_id": self.tenant_id,
            "human_confirmation": True,
            "automated_confirmation": False,
            "confirmed_by": actor_id,
            "confirmed_at": self._now(),
            **p,
        })

    def confirm_systemic_failure_classification(self, actor_id: str, p: dict):
        if p.get("actor_role") not in CLASSIFICATION_ROLES:
            raise PermissionError("authorized human systemic remediation-failure classification confirmation required")
        if not p.get("investigation_version_id") or not p.get("classification_analysis_version_id") or not p.get("evidence_refs"):
            raise ValueError("investigation, classification analysis and evidence references required")
        return self._immutable({
            "systemic_remediation_failure_classification_version_id": str(uuid4()),
            "tenant_id": self.tenant_id,
            "human_confirmation": True,
            "automated_confirmation": False,
            "confirmed_by": actor_id,
            "confirmed_at": self._now(),
            **p,
        })

    def create_strategy_candidate(self, actor_id: str, p: dict):
        required = ["release102_enterprise_recovery_reopening_version_id", "investigation_version_id", "root_cause_confirmation_version_id", "systemic_remediation_failure_classification_version_id"]
        if any(not p.get(k) for k in required) or not p.get("evidence_refs"):
            raise ValueError("Release 102 reopening, investigation, human confirmations and evidence are required")
        return self._immutable({
            "renewed_enterprise_remediation_strategy_candidate_version_id": str(uuid4()),
            "tenant_id": self.tenant_id,
            "recommendation_only": True,
            "human_authorization_required": True,
            "prepared_by": actor_id,
            "prepared_at": self._now(),
            **p,
        })

    def independent_challenge(self, actor_id: str, p: dict):
        if p.get("reviewer_role") not in INDEPENDENT_ROLES:
            raise PermissionError("independent internal-audit human reviewer required")
        if p.get("investigation_owner_actor_id") and str(p.get("investigation_owner_actor_id")) == str(actor_id):
            raise PermissionError("segregation of duties: investigation owner cannot independently challenge own investigation")
        required = ["investigation_version_id", "strategy_candidate_version_id", "systemic_remediation_failure_classification_version_id"]
        if any(not p.get(k) for k in required) or not p.get("evidence_refs"):
            raise ValueError("investigation, strategy, classification and evidence references required")
        return self._immutable({
            "enterprise_remediation_independent_challenge_version_id": str(uuid4()),
            "tenant_id": self.tenant_id,
            "human_decision": True,
            "automated_decision": False,
            "segregation_of_duties_confirmed": True,
            "decided_by": actor_id,
            "decided_at": self._now(),
            **p,
        })

    def conclude_investigation(self, actor_id: str, p: dict):
        if p.get("investigator_role") not in INVESTIGATOR_ROLES:
            raise PermissionError("authorized human enterprise remediation investigator required")
        if not p.get("investigation_version_id") or not p.get("evidence_refs"):
            raise ValueError("investigation and evidence references required")
        return self._immutable({
            "reopened_reauthorized_enterprise_remediation_investigation_conclusion_version_id": str(uuid4()),
            "tenant_id": self.tenant_id,
            "human_conclusion": True,
            "automated_conclusion": False,
            "concluded_by": actor_id,
            "concluded_at": self._now(),
            **p,
        })

    def authorize_enterprise_remediation(self, actor_id: str, p: dict):
        if p.get("actor_role") not in EXECUTIVE_ROLES:
            raise PermissionError("authorized executive human enterprise remediation reauthorization required")
        required = [
            "release102_enterprise_recovery_reopening_version_id", "investigation_version_id", "investigation_conclusion_version_id",
            "root_cause_confirmation_version_id", "systemic_remediation_failure_classification_version_id", "strategy_candidate_version_id",
            "independent_challenge_version_id",
        ]
        if any(not p.get(k) for k in required) or not p.get("evidence_refs"):
            raise ValueError("complete evidence-bound investigation, confirmation, strategy and challenge references required")
        readiness = enterprise_remediation_reauthorization_readiness(p.get("readiness", {}))
        if p.get("decision") == "authorize" and not readiness["ready_for_human_enterprise_remediation_reauthorization"]:
            raise ValueError("enterprise remediation reauthorization gates are incomplete")
        return self._immutable({
            "enterprise_remediation_reauthorization_version_id": str(uuid4()),
            "tenant_id": self.tenant_id,
            "human_reauthorization": True,
            "automated_reauthorization": False,
            "reauthorized_by": actor_id,
            "reauthorized_at": self._now(),
            "readiness_result": readiness,
            **p,
        })
