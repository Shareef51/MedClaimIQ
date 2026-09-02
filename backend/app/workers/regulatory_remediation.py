from app.db.session import SessionLocal
from app.services.regulatory_remediation import RegulatoryRemediationService

def run_tenant(tenant_id:str):
    # Monitoring-only: ages remediation plans/tasks and raises derived alerts.
    # It never approves remediation, completes tasks, retests controls, certifies closure,
    # represents a human regulator, posts accounting, authorizes payments, collects funds, or moves money.
    with SessionLocal() as db:
        result=RegulatoryRemediationService(db,tenant_id).refresh_operations(actor_id="regulatory-remediation-worker",actor_type="monitoring_worker")
        db.commit();return result

def run_all_tenants(tenant_ids):return sum(run_tenant(t) for t in tenant_ids)
