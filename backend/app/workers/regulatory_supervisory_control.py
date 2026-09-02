from app.db.session import SessionLocal
from app.services.regulatory_supervisory_control import RegulatorySupervisoryControlService

def run_tenant(tenant_id:str):
    # Monitoring-only worker: creates/refreshes derived reconciliation cases and aging signals.
    # It never certifies reconciliation, authorizes submission, posts accounting, authorizes payment, collects, or moves funds.
    with SessionLocal() as db:
        result=RegulatorySupervisoryControlService(db,tenant_id).refresh_cases(actor_id="regulatory-supervision-worker",actor_type="monitoring_worker")
        db.commit();return result["created"]+result["updated"]

def run_all_tenants(tenant_ids):return sum(run_tenant(t) for t in tenant_ids)
