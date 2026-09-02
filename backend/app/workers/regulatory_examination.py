from app.db.session import SessionLocal
from app.services.regulatory_examination import RegulatoryExaminationService

def run_tenant(tenant_id:str):
    # Monitoring-only worker: ages examination/inquiry work and raises derived supervisory escalations.
    # It never drafts or approves responses, represents a human regulator, alters accounting/financial records,
    # authorizes payments, collects funds, or moves money.
    with SessionLocal() as db:
        result=RegulatoryExaminationService(db,tenant_id).refresh_operations(actor_id="regulatory-examination-worker",actor_type="monitoring_worker")
        db.commit();return result

def run_all_tenants(tenant_ids):return sum(run_tenant(t) for t in tenant_ids)
