from app.db.session import SessionLocal
from app.repositories.regulatory_post_closure_surveillance import RegulatoryPostClosureSurveillanceRepository

def run_tenant(tenant_id:str)->dict:
    with SessionLocal() as session:
        repo=RegulatoryPostClosureSurveillanceRepository(session,tenant_id)
        signals=repo.signals(); candidates=repo.candidates()
        # Monitoring-only worker: never performs human reopening decisions.
        return {"tenant_id":tenant_id,"signals":len(signals),"pending_candidates":sum(c.status=="pending_human_review" for c in candidates),"write_authority":"monitoring_only"}

def run_all_tenants(tenant_ids:list[str]): return [run_tenant(t) for t in tenant_ids]
