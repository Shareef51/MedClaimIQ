from __future__ import annotations
from typing import TypedDict
class ProviderDisputeState(TypedDict,total=False):
    dispute_id:str;snapshot_id:str;rag_run_id:str;recommendation_run_id:str;stage:str;requires_human_review:bool;adjudication_authority:str

def provider_dispute_graph_contract()->dict[str,object]:
    return {"stages":["validate_provider_evidence","reingest_multimodal","lock_dispute_snapshot","retrieve_contract_policy","compare_recovery_vs_dispute","detect_policy_contradictions","recommendation_only_agent","independent_human_dispute_gate"],"terminal_stage":"independent_human_dispute_gate","terminal_requires_human":True,"adjudication_authority":"none","forbidden_nodes":["resolve_dispute","post_journal","authorize_payment","collect_funds","move_money"]}
