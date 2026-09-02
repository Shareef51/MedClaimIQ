from __future__ import annotations
from app.db.session import SessionLocal
from app.services.financial_intelligence import FinancialIntelligenceService

def run_tenant(tenant_id:str,session_factory=SessionLocal)->int:
    """Refresh immutable derived intelligence snapshots and OTel metrics only.

    Deliberately contains no journal posting, reserve source mutation, payment authorization, accounting
    close, adjudication, settlement handoff, adjustment approval, or fund-movement operations.
    """
    with session_factory() as db:
        try:
            result=FinancialIntelligenceService(db,tenant_id).portfolio_system(persist=True);db.commit();return int(result["kpis"]["claims_analyzed"])
        except Exception:
            db.rollback();raise

def run_all_tenants(tenant_ids:list[str],session_factory=SessionLocal)->int:
    return sum(run_tenant(t,session_factory) for t in tenant_ids)
