from __future__ import annotations
from datetime import datetime, timezone
from uuid import uuid4
from app.evaluation.regulatory_examination_reopened_reauthorized_recovery_investigation import *

EXECUTIVE_ROLES = {"chief_risk_officer", "chief_compliance_officer", "executive_risk_committee", "executive_certifier"}
INDEPENDENT_ROLES = {"internal_auditor", "chief_audit_executive", "independent_assurance", "independent_validator"}
INVESTIGATOR_ROLES = INDEPENDENT_ROLES | {"regulatory_affairs", "compliance_reviewer", "remediation_governance"}

class RegulatoryExaminationReopenedReauthorizedRecoveryInvestigationService:
    def __init__(self, db, tenant_id: str): self.db = db; self.tenant_id = tenant_id
    def _now(self): return datetime.now(timezone.utc).isoformat()
    def _immutable(self, payload): payload["version_hash"] = version_hash(payload); return payload

    def create_investigation(self, actor_id, p):
        if p.get("actor_role") not in INVESTIGATOR_ROLES:
            raise PermissionError("authorized independent/human reopened-recovery investigator required")
        if not p.get("release90_reopening_version_id"):
            raise ValueError("immutable Release 90 human enterprise reopening decision reference required")
        if not p.get("surveillance_version_refs") or not p.get("evidence_refs"):
            raise ValueError("surveillance and evidence references required")
        return self._immutable({
            "reopened_reauthorized_recovery_investigation_version_id": str(uuid4()),
            "tenant_id": self.tenant_id,
            "human_investigation": True,
            "automated_investigation_opening": False,
            "opened_by": actor_id,
            "opened_at": self._now(),
            **p,
        })

    def reconstruct_evidence(self, p): return {"tenant_id": self.tenant_id, "analysis_only": True, **reconstruct_reopened_recovery_cycles(p)}
    def reconstruct_root_causes(self, p): return {"tenant_id": self.tenant_id, "recommendation_only": True, **reconstruct_repeated_failure_root_causes(p)}
    def reassess_assumptions(self, p): return {"tenant_id": self.tenant_id, "analysis_only": True, **reassess_prior_recertification_assumptions(p)}
    def analyze_re_rehabilitation(self, p): return {"tenant_id": self.tenant_id, "recommendation_only": True, **analyze_re_rehabilitation_failures(p)}
    def causal_map(self, p): return {"tenant_id": self.tenant_id, "analysis_only": True, **map_reopened_cross_entity_causality(p)}
    def regulator_impact(self, p): return {"tenant_id": self.tenant_id, "analysis_only": True, **regulator_followup_impact(p)}

    def create_strategy_candidate(self, actor_id, p):
        if not p.get("release90_reopening_version_id") or not p.get("investigation_version_id"):
            raise ValueError("Release 90 reopening and reopened investigation references required")
        return self._immutable({
            "renewed_reauthorized_recovery_strategy_candidate_version_id": str(uuid4()),
            "tenant_id": self.tenant_id,
            "created_by": actor_id,
            "created_at": self._now(),
            "recommendation_only": True,
            "human_reauthorization_required": True,
            **p,
        })

    def independent_challenge(self, actor_id, p):
        if p.get("reviewer_role") not in INDEPENDENT_ROLES:
            raise PermissionError("independent internal-audit human challenge required")
        if not p.get("investigation_version_id") or not p.get("strategy_candidate_version_id"):
            raise ValueError("investigation and strategy candidate references required")
        return self._immutable({
            "reopened_recovery_independent_challenge_version_id": str(uuid4()),
            "tenant_id": self.tenant_id,
            "human_decision": True,
            "automated_decision": False,
            "decided_by": actor_id,
            "decided_at": self._now(),
            **p,
        })

    def conclude_investigation(self, actor_id, p):
        if p.get("investigator_role") not in INVESTIGATOR_ROLES:
            raise PermissionError("authorized human reopened-recovery investigator required")
        if not p.get("investigation_version_id"):
            raise ValueError("reopened recovery investigation reference required")
        if not p.get("evidence_refs"):
            raise ValueError("evidence-bound human investigation conclusion required")
        return self._immutable({
            "reopened_recovery_investigation_conclusion_version_id": str(uuid4()),
            "tenant_id": self.tenant_id,
            "human_conclusion": True,
            "automated_conclusion": False,
            "concluded_by": actor_id,
            "concluded_at": self._now(),
            **p,
        })

    def readiness(self, p): return {"tenant_id": self.tenant_id, **recovery_reauthorization_readiness(p)}

    def authorize_recovery(self, actor_id, p):
        if p.get("actor_role") not in EXECUTIVE_ROLES:
            raise PermissionError("authorized executive human supervisory recovery reauthorization required")
        required = [
            "release90_reopening_version_id",
            "investigation_version_id",
            "investigation_conclusion_version_id",
            "strategy_candidate_version_id",
            "independent_challenge_version_id",
        ]
        if any(not p.get(k) for k in required):
            raise ValueError("reopening, investigation, conclusion, strategy and independent challenge references required")
        result = recovery_reauthorization_readiness(p.get("readiness", {}))
        if p.get("decision") == "authorize" and not result["ready_for_human_supervisory_reauthorization"]:
            raise ValueError("supervisory recovery reauthorization gates are incomplete")
        return self._immutable({
            "supervisory_recovery_reauthorization_version_id": str(uuid4()),
            "tenant_id": self.tenant_id,
            "human_reauthorization": True,
            "automated_reauthorization": False,
            "reauthorized_by": actor_id,
            "reauthorized_at": self._now(),
            "readiness_result": result,
            **p,
        })
