from __future__ import annotations
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.services.accounting_ledger import AccountingLedgerService

def run_tenant(tenant_id:str,session_factory=SessionLocal)->int:
    """Refresh reconciliation aging/priority metadata only.

    This worker contains no journal posting, finance authorization, period-close, recoupment approval,
    payment handoff, bank instruction, or fund-movement capability.
    """
    with session_factory() as db:
        try:
            rows=AccountingLedgerService(db,tenant_id).refresh_aging_queue_system();db.commit();return len(rows)
        except Exception:
            db.rollback();raise

def run_all_tenants(tenant_ids:list[str],session_factory=SessionLocal)->int:
    return sum(run_tenant(t,session_factory) for t in tenant_ids)
