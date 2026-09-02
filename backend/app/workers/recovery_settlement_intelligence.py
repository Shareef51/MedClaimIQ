from __future__ import annotations
import time
from app.db.session import get_session_factory
from app.services.recovery_settlement_intelligence import RecoverySettlementIntelligenceService

def run_tenant_once(tenant_id:str)->int:
    """Refresh immutable derived intelligence/OTel only; never mutate Release 47 source financial state."""
    with get_session_factory()() as db:
        count=RecoverySettlementIntelligenceService(db,tenant_id).refresh_system();db.commit();return count

def run_all_tenants(active_tenant_ids,poll_seconds:float=60.0)->None:
    while True:
        for tenant_id in active_tenant_ids():run_tenant_once(tenant_id)
        time.sleep(max(1.0,poll_seconds))
# No balance mutation, settlement evidence verification, journal posting, payment instruction, closeout certificate decision, bank transaction, collection, or fund movement.
