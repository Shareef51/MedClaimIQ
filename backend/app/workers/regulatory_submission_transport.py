from app.db.session import SessionLocal
from app.services.regulatory_submission_transport import RegulatorySubmissionTransportService

def run_tenant(tenant_id:str,worker_id:str="regulatory-transport-worker"):
    with SessionLocal() as db:
        tx=RegulatorySubmissionTransportService(db,tenant_id).lease_and_dispatch(worker_id)
        db.commit();return None if tx is None else tx.transmission_id

def run_all_tenants(tenant_ids):
    return sum(run_tenant(t) is not None for t in tenant_ids)
