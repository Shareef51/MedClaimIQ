from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field

class CasesRequest(BaseModel): cases:list[dict[str,Any]]=Field(default_factory=list)
class SupplyChainAssessmentRequest(BaseModel):
    secret_scan_passed:bool=False; secret_findings:int=0; dependency_scan_passed:bool=False; critical_vulnerabilities:int=0; high_vulnerabilities:int=0
    sbom_present:bool=False; provenance_present:bool=False; images_signed:bool=False; container_scan_passed:bool=False; non_root_containers:bool=False
    iac_scan_passed:bool=False; network_policies_present:bool=False; secrets_externalized:bool=False
class SecurityReleaseReadinessRequest(BaseModel):
    candidate_version:str|None=None; release107_release_candidate_decision_version_id:str|None=None; gates:dict[str,Any]=Field(default_factory=dict); findings:list[dict[str,Any]]=Field(default_factory=list); approved_waivers:list[dict[str,Any]]=Field(default_factory=list); controls:list[dict[str,Any]]=Field(default_factory=list); evidence_refs:list[str]=Field(default_factory=list); sbom_ref:str|None=None; security_report_ref:str|None=None; frameworks:list[str]=Field(default_factory=list)
class SecurityRedTeamRunCreate(SecurityReleaseReadinessRequest):
    release_id:str; actor_role:str; attack_surface_results:dict[str,Any]=Field(default_factory=dict)
class SecurityWaiverCreate(BaseModel):
    release_id:str; actor_role:str; finding_id:str; severity:Literal["low","medium","high","critical"]; category:str; rationale:str; compensating_controls:list[str]=Field(default_factory=list); expires_at:str; evidence_refs:list[str]=Field(default_factory=list)
class SecurityCertificationCreate(BaseModel):
    release_id:str; candidate_version:str; actor_role:str; release107_release_candidate_decision_version_id:str; security_red_team_run_version_id:str; readiness:dict[str,Any]=Field(default_factory=dict); decision:Literal["certify","reject","defer"]; rationale:str; evidence_refs:list[str]=Field(default_factory=list); compliance_evidence_pack_hash:str|None=None
