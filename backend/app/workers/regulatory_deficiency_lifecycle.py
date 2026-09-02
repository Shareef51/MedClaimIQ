from datetime import UTC,datetime
from app.db.session import get_session_factory,set_tenant_context
from app.repositories.regulatory_deficiency_lifecycle import RegulatoryDeficiencyLifecycleRepository

def run_tenant_once(tenant_id:str)->dict:
    with get_session_factory()() as db:
        set_tenant_context(db,tenant_id); repo=RegulatoryDeficiencyLifecycleRepository(db,tenant_id); now=datetime.now(UTC); plans=repo.plans()
        result={"tenant_id":tenant_id,"overdue_corrective_actions":sum(p.status not in {"closed","cancelled"} and p.due_at<now for p in plans),"monitoring_only":True,"human_approval_required":True}
        db.commit(); return result

def run_all_tenants(active_tenant_ids):
    for tenant_id in active_tenant_ids(): run_tenant_once(tenant_id)
