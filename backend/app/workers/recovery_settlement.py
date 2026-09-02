from __future__ import annotations
import time
from app.db.session import get_session_factory
from app.services.recovery_settlement import RecoverySettlementService

def run_tenant_once(tenant_id:str)->int:
    with get_session_factory()() as db:
        created=RecoverySettlementService(db,tenant_id).refresh_operational_exceptions();db.commit();return created

def run_all_tenants(active_tenant_ids,poll_seconds:float=30.0)->None:
    while True:
        for tenant_id in active_tenant_ids():run_tenant_once(tenant_id)
        time.sleep(max(1.0,poll_seconds))
# Deliberately no evidence verification, ledger posting, closeout approval, payment authorization, collection or bank transaction calls.
