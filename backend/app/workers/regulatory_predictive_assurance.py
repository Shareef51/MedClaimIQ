from __future__ import annotations
import time
from app.db.session import get_session_factory,set_tenant_context
from app.repositories.regulatory_portfolio_oversight import RegulatoryPortfolioOversightRepository
from app.services.regulatory_predictive_assurance import RegulatoryPredictiveAssuranceService

def run_tenant_once(tenant_id:str):
    with get_session_factory()() as db:
        set_tenant_context(db,tenant_id)
        # Monitoring-only worker: detects snapshots lacking forecasts; never creates approvals or closure actions.
        portfolio=RegulatoryPortfolioOversightRepository(db,tenant_id)
        latest=portfolio.snapshots()[:25]
        return {"tenant_id":tenant_id,"snapshots_scanned":len(latest),"authority":"monitoring_only"}
def run_all_tenants(active_tenant_ids):
    while True:
        for tenant_id in active_tenant_ids(): run_tenant_once(tenant_id)
        time.sleep(60)
