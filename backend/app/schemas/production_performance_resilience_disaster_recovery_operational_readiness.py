from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field

class LoadStressSoakRequest(BaseModel): profiles:list[dict[str,Any]]=Field(default_factory=list); minimum_soak_minutes:int=60
class CasesRequest(BaseModel): cases:list[dict[str,Any]]=Field(default_factory=list)
class ComponentsRequest(BaseModel): components:list[dict[str,Any]]=Field(default_factory=list)
class DrillsRequest(BaseModel): drills:list[dict[str,Any]]=Field(default_factory=list)
class BackupRestoreRequest(BaseModel): stores:list[dict[str,Any]]=Field(default_factory=list)
class ServicesRequest(BaseModel): services:list[dict[str,Any]]=Field(default_factory=list)
class CapacityRequest(BaseModel): services:list[dict[str,Any]]=Field(default_factory=list); forecast_horizon_days:int=30
class ObservabilityRequest(BaseModel): surfaces:list[dict[str,Any]]=Field(default_factory=list)
class IncidentExerciseRequest(BaseModel): exercises:list[dict[str,Any]]=Field(default_factory=list)
class OperationalReadinessRequest(BaseModel):
    release_id:str|None=None; candidate_version:str|None=None
    release107_release_candidate_decision_version_id:str|None=None
    release108_release_security_certification_version_id:str|None=None
    gates:dict[str,Any]=Field(default_factory=dict)
    open_operational_risks:list[dict[str,Any]]=Field(default_factory=list)
    evidence_refs:list[str]=Field(default_factory=list); runbook_refs:list[str]=Field(default_factory=list); dashboard_refs:list[str]=Field(default_factory=list); drill_refs:list[str]=Field(default_factory=list)
class OperationalDrillRunCreate(OperationalReadinessRequest): actor_role:str; environment:str="preproduction"; suite_name:str="operational-go-live-readiness"; drill_results:dict[str,Any]=Field(default_factory=dict)
class OperationalCertificationCreate(BaseModel):
    release_id:str; candidate_version:str; actor_role:str
    release107_release_candidate_decision_version_id:str
    release108_release_security_certification_version_id:str
    operational_drill_run_version_id:str
    readiness:dict[str,Any]=Field(default_factory=dict)
    decision:Literal["certify","reject","defer"]
    rationale:str; evidence_refs:list[str]=Field(default_factory=list); operational_evidence_pack_hash:str|None=None
