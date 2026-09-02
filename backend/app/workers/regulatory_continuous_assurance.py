from __future__ import annotations
import time
from app.db.session import get_session_factory,set_tenant_context
from app.repositories.regulatory_continuous_assurance import RegulatoryContinuousAssuranceRepository

def run_tenant_once(tenant_id:str):
    with get_session_factory()() as db:
        set_tenant_context(db,tenant_id);repo=RegulatoryContinuousAssuranceRepository(db,tenant_id)
        open_drifts=repo.drifts(status="open")[:100]
        # Monitoring-only worker: surfaces stale/open assurance signals. It never approves remediation or executes corrective action.
        return {"tenant_id":tenant_id,"open_drifts_scanned":len(open_drifts),"material_drifts":sum(x.severity in {"high","critical"} for x in open_drifts),"authority":"monitoring_only"}
def run_all_tenants(active_tenant_ids):
    while True:
        for tenant_id in active_tenant_ids():run_tenant_once(tenant_id)
        time.sleep(60)
