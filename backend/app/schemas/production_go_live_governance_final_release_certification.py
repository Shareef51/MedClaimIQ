from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field
class ReleaseManifestRequest(BaseModel):
    release_id:str; candidate_version:str; git_commit_sha:str; image_digest:str; sbom_digest:str; migration_head:str; expected_migration_head:str="0105_final_production_go_live"; configuration_fingerprint:str; evidence_refs:list[str]=Field(default_factory=list)
class PreflightRequest(BaseModel): checks:list[dict[str,Any]]=Field(default_factory=list); required_checks:list[str]=Field(default_factory=list)
class CanaryRequest(BaseModel): stages:list[dict[str,Any]]=Field(default_factory=list); rollback_ready:bool=False; rollback_artifact_verified:bool=False
class PostDeployRequest(BaseModel): surfaces:list[dict[str,Any]]=Field(default_factory=list); smoke_tests_passed:bool=False; synthetic_claim_journey_passed:bool=False; ai_rag_agent_verification_passed:bool=False
class HypercareRequest(BaseModel): incident_commander_assigned:bool=False; oncall_routes_verified:bool=False; dashboards_verified:bool=False; rollback_owner_assigned:bool=False; communications_plan_ready:bool=False; slo_window_passed:bool=False; open_sev1:int=0; open_sev2:int=0
class FinalReadinessRequest(BaseModel):
    release_id:str; candidate_version:str; release107_release_candidate_decision_version_id:str|None=None; release108_release_security_certification_version_id:str|None=None; release109_operational_readiness_certification_version_id:str|None=None; gates:dict[str,bool]=Field(default_factory=dict); open_release_risks:list[dict[str,Any]]=Field(default_factory=list); evidence_refs:list[str]=Field(default_factory=list)
class FinalReleaseManifestCreate(FinalReadinessRequest):
    actor_role:str; git_commit_sha:str; image_digest:str; sbom_digest:str; migration_head:str; configuration_fingerprint:str
class GoLiveApprovalCreate(FinalReadinessRequest):
    actor_role:str; final_release_manifest_version_id:str; decision:str; rationale:str
class DeploymentVerificationCreate(BaseModel):
    actor_role:str; release_id:str; candidate_version:str; final_release_manifest_version_id:str; go_live_approval_version_id:str; environment:str="production"; verification:dict[str,Any]; evidence_refs:list[str]=Field(default_factory=list)
class FinalReleaseCertificationCreate(BaseModel):
    actor_role:str; release_id:str; candidate_version:str; release107_release_candidate_decision_version_id:str; release108_release_security_certification_version_id:str; release109_operational_readiness_certification_version_id:str; final_release_manifest_version_id:str; go_live_approval_version_id:str; deployment_verification_version_id:str; decision:str; rationale:str; evidence_refs:list[str]=Field(default_factory=list)
class HypercareCheckpointCreate(HypercareRequest):
    actor_role:str; release_id:str; final_release_certification_version_id:str; checkpoint_name:str; evidence_refs:list[str]=Field(default_factory=list)
class HypercareClosureCreate(HypercareRequest):
    actor_role:str; release_id:str; final_release_certification_version_id:str; decision:str; rationale:str; evidence_refs:list[str]=Field(default_factory=list)
