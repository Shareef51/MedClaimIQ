from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
from uuid import uuid4

from app.agents.multimodal_context import MultimodalAgentContext, MultimodalAgentEvidenceItem, pack_sha256
from app.domain.advanced_rag import Answerability
from app.domain.multimodal_agent_orchestration import MULTIMODAL_AGENT_PROFILES, MultimodalAgentEscalation
from app.domain.multimodal_rag import InconsistencySeverity
from app.domain.orchestration import AgentFinding, AgentName
from app.domain.rag import RetrievalScope
from app.models.multimodal_agent_orchestration import MultimodalAgentEventModel, MultimodalAgentInvestigationModel
from app.repositories.claims import ClaimRepository
from app.repositories.multimodal_agent_orchestration import MultimodalAgentOrchestrationRepository


class MultimodalAgentOrchestrationError(RuntimeError): pass


class MultimodalAgentInvestigationService:
    def __init__(self, *, session, tenant_id: str, retrieval_service) -> None:
        self.session=session; self.tenant_id=tenant_id; self.retrieval_service=retrieval_service
        self.repo=MultimodalAgentOrchestrationRepository(session, tenant_id)

    def prepare(self, *, workflow_id: str, claim_id: str, agent: AgentName, attempt: int, trace_id: str|None=None) -> MultimodalAgentContext | None:
        profile=MULTIMODAL_AGENT_PROFILES.get(agent)
        if profile is None: return None
        claim=ClaimRepository(self.session,self.tenant_id).get(claim_id)
        if claim is None: raise MultimodalAgentOrchestrationError("claim missing in multimodal investigation scope")
        requested,required=profile.clamp_modalities()
        scope=RetrievalScope(
            tenant_id=self.tenant_id, claim_id=claim_id, patient_subject_id=claim.patient_subject_id,
            domains=profile.domains, acl_tags=("claim_authorized",), minimum_authority_rank=0,
        )
        result=self.retrieval_service.search(
            query=profile.query_template, scope=scope, agent=agent,
            requested_modalities=requested, required_modalities=required,
            limit=profile.max_items, trace_id=trace_id,
        )
        pack=result.pack
        reasons=[]
        material=[x for x in pack.inconsistencies if x.severity==InconsistencySeverity.MATERIAL]
        blocking=[x for x in pack.gaps if x.blocking]
        present={x.modality for x in pack.items}
        missing=[m for m in required if m not in present]
        if material: reasons.append(MultimodalAgentEscalation.MATERIAL_CONFLICT.value)
        if missing: reasons.append(MultimodalAgentEscalation.MISSING_REQUIRED_MODALITY.value)
        if pack.answerability==Answerability.INSUFFICIENT or blocking:
            reasons.append(MultimodalAgentEscalation.INSUFFICIENT_MULTIMODAL_EVIDENCE.value)
        reasons=list(dict.fromkeys(reasons))
        investigation_id=f"mai_{uuid4().hex}"
        pack_hash=pack_sha256(pack)
        now=datetime.now(UTC)
        row=MultimodalAgentInvestigationModel(
            investigation_id=investigation_id, tenant_id=self.tenant_id, claim_id=claim_id, workflow_id=workflow_id,
            agent_name=agent.value, attempt=attempt, multimodal_run_id=result.run_id, pack_id=pack.pack_id,
            pack_sha256=pack_hash, query_sha256=sha256(profile.query_template.encode()).hexdigest(),
            requested_modalities=[m.value for m in requested], required_modalities=[m.value for m in required],
            answerability=pack.answerability.value, confidence=pack.confidence,
            material_inconsistency_count=len(material), blocking_gap_count=len(blocking),
            human_review_required=bool(reasons), escalation_reasons=reasons, trace_id=trace_id, created_at=now,
        )
        self.repo.add_investigation(row)
        self.repo.add_event(MultimodalAgentEventModel(
            event_id=f"mae_{uuid4().hex}", tenant_id=self.tenant_id, claim_id=claim_id, workflow_id=workflow_id,
            investigation_id=investigation_id, agent_name=agent.value, event_type="multimodal.investigation.completed",
            event_payload={"pack_id":pack.pack_id,"answerability":pack.answerability.value,"item_count":len(pack.items),"escalation_reasons":reasons},
            trace_id=trace_id, created_at=now,
        ))
        items=tuple(MultimodalAgentEvidenceItem(
            evidence_key=f"mm:{x.item_id}", item_id=x.item_id, modality=x.modality, text=x.text,
            source_id=x.source_id, source_version=x.source_version, authority_rank=x.authority_rank,
            confidence=x.confidence, citation=x.citation.as_dict(),
        ) for x in pack.items)
        inconsistencies=tuple({
            "code":x.code,"field":x.field,"severity":x.severity.value,
            "left_evidence_key":f"mm:{x.left_item_id}","right_evidence_key":f"mm:{x.right_item_id}",
            "confidence":x.confidence,"description":x.description,
        } for x in pack.inconsistencies)
        gaps=tuple({"code":x.code,"description":x.description,"blocking":x.blocking,"modality":x.modality.value if x.modality else None} for x in pack.gaps)
        return MultimodalAgentContext(
            investigation_id=investigation_id, agent=agent, pack_id=pack.pack_id, run_id=result.run_id,
            pack_sha256=pack_hash, answerability=pack.answerability, confidence=pack.confidence,
            required_modalities=required, items=items, inconsistencies=inconsistencies, gaps=gaps,
            human_review_required=bool(reasons), escalation_reasons=tuple(reasons),
        )


def deterministic_multimodal_review_finding(agent: AgentName, context: MultimodalAgentContext) -> AgentFinding | None:
    if not context.human_review_required: return None
    keys=tuple(item.evidence_key for item in context.items[:8])
    return AgentFinding(
        agent=agent, finding_id=f"af_mm_{uuid4().hex}",
        summary="Multimodal investigation requires human review because evidence conflicts, required modalities are missing, or evidence is insufficient.",
        confidence=max(0.0,min(1.0,context.confidence)), evidence_keys=keys,
        risk_flags=tuple(context.escalation_reasons), requires_human_review=True,
        metadata={
            "deterministic_multimodal_escalation":True,"multimodal_pack_id":context.pack_id,
            "multimodal_run_id":context.run_id,"investigation_id":context.investigation_id,
            "answerability":context.answerability.value,"escalation_reasons":list(context.escalation_reasons),
            "multimodal_citations":{i.evidence_key:i.citation for i in context.items[:12]},
        },
    )
