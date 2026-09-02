from __future__ import annotations

from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class MultimodalAgentInvestigationModel(Base):
    __tablename__="multimodal_agent_investigations"
    __table_args__=(
        Index("ix_multimodal_agent_investigation_workflow","tenant_id","workflow_id","created_at"),
        Index("ix_multimodal_agent_investigation_pack","tenant_id","pack_id"),
    )
    investigation_id: Mapped[str]=mapped_column(String(128),primary_key=True)
    tenant_id: Mapped[str]=mapped_column(ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False,index=True)
    claim_id: Mapped[str]=mapped_column(ForeignKey("claims.claim_id",ondelete="CASCADE"),nullable=False,index=True)
    workflow_id: Mapped[str]=mapped_column(ForeignKey("agent_workflows.workflow_id",ondelete="CASCADE"),nullable=False,index=True)
    agent_name: Mapped[str]=mapped_column(String(80),nullable=False)
    attempt: Mapped[int]=mapped_column(Integer,nullable=False)
    multimodal_run_id: Mapped[str]=mapped_column(ForeignKey("multimodal_rag_runs.run_id",ondelete="RESTRICT"),nullable=False)
    pack_id: Mapped[str]=mapped_column(ForeignKey("multimodal_evidence_packs.pack_id",ondelete="RESTRICT"),nullable=False)
    pack_sha256: Mapped[str]=mapped_column(String(64),nullable=False)
    query_sha256: Mapped[str]=mapped_column(String(64),nullable=False)
    requested_modalities: Mapped[list]=mapped_column(JSON,nullable=False,default=list)
    required_modalities: Mapped[list]=mapped_column(JSON,nullable=False,default=list)
    answerability: Mapped[str]=mapped_column(String(30),nullable=False)
    confidence: Mapped[float]=mapped_column(Float,nullable=False)
    material_inconsistency_count: Mapped[int]=mapped_column(Integer,nullable=False,default=0)
    blocking_gap_count: Mapped[int]=mapped_column(Integer,nullable=False,default=0)
    human_review_required: Mapped[bool]=mapped_column(Boolean,nullable=False,default=False)
    escalation_reasons: Mapped[list]=mapped_column(JSON,nullable=False,default=list)
    trace_id: Mapped[str|None]=mapped_column(String(128),nullable=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False)


class MultimodalAgentEventModel(Base):
    __tablename__="multimodal_agent_events"
    __table_args__=(Index("ix_multimodal_agent_event_workflow","tenant_id","workflow_id","created_at"),)
    event_id: Mapped[str]=mapped_column(String(128),primary_key=True)
    tenant_id: Mapped[str]=mapped_column(ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False,index=True)
    claim_id: Mapped[str]=mapped_column(ForeignKey("claims.claim_id",ondelete="CASCADE"),nullable=False,index=True)
    workflow_id: Mapped[str]=mapped_column(ForeignKey("agent_workflows.workflow_id",ondelete="CASCADE"),nullable=False,index=True)
    investigation_id: Mapped[str]=mapped_column(ForeignKey("multimodal_agent_investigations.investigation_id",ondelete="CASCADE"),nullable=False,index=True)
    agent_name: Mapped[str]=mapped_column(String(80),nullable=False)
    event_type: Mapped[str]=mapped_column(String(100),nullable=False)
    event_payload: Mapped[dict]=mapped_column(JSON,nullable=False,default=dict)
    trace_id: Mapped[str|None]=mapped_column(String(128),nullable=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False)
