from __future__ import annotations
import time
from app.db.session import get_session_factory,set_tenant_context
from app.repositories.regulatory_control_testing import RegulatoryControlTestingRepository

def run_tenant_once(tenant_id:str):
    with get_session_factory()() as db:
        set_tenant_context(db,tenant_id);repo=RegulatoryControlTestingRepository(db,tenant_id)
        runs=repo.runs()[:100]
        return {"tenant_id":tenant_id,"test_runs_scanned":len(runs),"open_runs":sum(r.status!="concluded" for r in runs),"authority":"orchestration_only"}
def run_all_tenants(active_tenant_ids):
    while True:
        for tenant_id in active_tenant_ids():run_tenant_once(tenant_id)
        time.sleep(60)
