#!/usr/bin/env python3
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from app.domain.production_security_privacy_compliance_red_team import REQUIRED_SECURITY_RELEASE_GATES
from app.evaluation.production_security_privacy_compliance_red_team import *
p=json.loads((ROOT/'sample-data/security/adversarial_attack_matrix.json').read_text())
results={
 'cross_tenant_penetration':assess_cross_tenant_penetration(p['cross_tenant']),
 'authorization_abuse':assess_authorization_abuse(p['authorization']),
 'prompt_injection_defense':assess_prompt_injection(p['prompt_injection']),
 'rag_poisoning_exfiltration_defense':assess_rag_poisoning_exfiltration(p['rag']),
 'mcp_tool_abuse_defense':assess_mcp_tool_abuse(p['mcp']),
 'agent_privilege_boundary':assess_agent_privilege_boundary(p['agent']),
 'phi_pii_leakage_prevention':assess_phi_pii_leakage(p['privacy']),
 'api_fuzzing':assess_api_fuzzing(p['api_fuzzing']),
 'audit_integrity':assess_audit_tamper(p['audit_tamper']),
 'adversarial_multimodal':assess_adversarial_multimodal(p['multimodal']),
}
supply=assess_supply_chain({'secret_scan_passed':True,'secret_findings':0,'dependency_scan_passed':True,'critical_vulnerabilities':0,'high_vulnerabilities':0,'sbom_present':True,'provenance_present':True,'images_signed':True,'container_scan_passed':True,'non_root_containers':True,'iac_scan_passed':True,'network_policies_present':True,'secrets_externalized':True})
gates={
 'cross_tenant_penetration':results['cross_tenant_penetration']['cross_tenant_penetration_passed'],
 'authorization_abuse':results['authorization_abuse']['authorization_abuse_passed'],
 'prompt_injection_defense':results['prompt_injection_defense']['prompt_injection_defense_passed'],
 'rag_poisoning_exfiltration_defense':results['rag_poisoning_exfiltration_defense']['rag_poisoning_exfiltration_defense_passed'],
 'mcp_tool_abuse_defense':results['mcp_tool_abuse_defense']['mcp_tool_abuse_defense_passed'],
 'agent_privilege_boundary':results['agent_privilege_boundary']['agent_privilege_boundary_passed'],
 'phi_pii_leakage_prevention':results['phi_pii_leakage_prevention']['phi_pii_leakage_prevention_passed'],
 'secret_scanning':supply['secret_scanning'],'dependency_vulnerability_scan':supply['dependency_vulnerability_scan'],'sbom_and_provenance':supply['sbom_and_provenance'],'container_security':supply['container_security'],'iac_security':supply['iac_security'],
 'api_fuzzing':results['api_fuzzing']['api_fuzzing_passed'],'audit_integrity':results['audit_integrity']['audit_integrity_passed'],'adversarial_multimodal':results['adversarial_multimodal']['adversarial_multimodal_passed'],'compliance_evidence_complete':True,
}
readiness=security_release_readiness({'candidate_version':p['candidate_version'],'release107_release_candidate_decision_version_id':'synthetic-human-release107-decision','gates':gates,'findings':[],'approved_waivers':[],'evidence_refs':['synthetic:red-team-matrix','artifact:release108-readiness-design'],'sbom_ref':'ci:cyclonedx-sbom','security_report_ref':'ci:scanner-aggregate'})
out={'fixture_case_count':p['case_count'],'attack_surface_results':results,'supply_chain_fixture':supply,'security_release_readiness':readiness,'note':'Deterministic synthetic security harness validation only; human certification requires actual CI scanner evidence.'}
print(json.dumps(out,indent=2));
if not all(gates.values()) or not readiness['release_security_ready']: raise SystemExit(1)
