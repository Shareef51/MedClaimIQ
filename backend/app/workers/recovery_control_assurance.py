from __future__ import annotations
import time
from app.db.session import get_session_factory,set_tenant_context
from app.services.recovery_control_assurance import RecoveryControlAssuranceService

def run_tenant_once(tenant_id:str)->int:
    with get_session_factory()() as db:
        set_tenant_context(db,tenant_id);count=RecoveryControlAssuranceService(db,tenant_id).refresh_system();db.commit();return count

def run_all_tenants(active_tenant_ids,poll_seconds:float=60.0):
    while True:
        for tenant_id in active_tenant_ids():run_tenant_once(tenant_id)
        time.sleep(max(5.0,poll_seconds))
