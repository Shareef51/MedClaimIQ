from __future__ import annotations
from app.db.session import get_session_factory,set_tenant_context
from app.repositories.regulatory_assurance_deficiencies import RegulatoryAssuranceDeficiencyRepository

def run_tenant_once(tenant_id:str)->dict:
    with get_session_factory()() as db:
        set_tenant_context(db,tenant_id);repo=RegulatoryAssuranceDeficiencyRepository(db,tenant_id)
        issues=repo.issues();open_escalations=sum(i.status in {"proposed","escalated"} for i in issues)
        db.commit();return {"tenant_id":tenant_id,"open_enterprise_assurance_issues":open_escalations,"monitoring_only":True}

def run_all_tenants(active_tenant_ids):
    for tenant_id in active_tenant_ids():run_tenant_once(tenant_id)
