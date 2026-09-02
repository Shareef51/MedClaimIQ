from __future__ import annotations
from datetime import UTC, datetime
from app.db.session import SessionLocal
from app.repositories.regulatory_closure_governance import RegulatoryClosureGovernanceRepository

def run_for_tenant(tenant_id:str)->dict:
    with SessionLocal() as session:
        repo=RegulatoryClosureGovernanceRepository(session,tenant_id)
        now=datetime.now(UTC); windows=repo.windows(); candidates=0
        for w in windows:
            if w.status=="monitoring" and w.ends_at<now and (w.recurrence_detected or w.observed_passes<w.required_observations):
                w.status="reopen_candidate"; candidates+=1
        session.commit(); return {"tenant_id":tenant_id,"reopen_candidates":candidates,"authority":"monitoring_only"}

def run_all_tenants(tenant_ids:list[str]): return [run_for_tenant(t) for t in tenant_ids]
