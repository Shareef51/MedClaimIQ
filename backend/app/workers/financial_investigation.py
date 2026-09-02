from __future__ import annotations
import time
from sqlalchemy import select
from app.db.session import get_session_factory,set_tenant_context
from app.models.financial_intelligence import FinancialAnomalyInvestigationModel
from app.models.financial_investigation import FinancialInvestigationCaseModel
from app.services.financial_investigation import FinancialInvestigationService

def run_tenant_once(tenant_id:str,limit:int=50)->int:
    created=0
    with get_session_factory()() as db:
        set_tenant_context(db,tenant_id)
        q=(select(FinancialAnomalyInvestigationModel).where(FinancialAnomalyInvestigationModel.tenant_id==tenant_id).order_by(FinancialAnomalyInvestigationModel.created_at).limit(limit))
        for inv in db.scalars(q):
            exists=db.scalar(select(FinancialInvestigationCaseModel.case_id).where(FinancialInvestigationCaseModel.tenant_id==tenant_id,FinancialInvestigationCaseModel.source_investigation_id==inv.investigation_id))
            if exists:continue
            FinancialInvestigationService(db,tenant_id).create_from_anomaly(inv.investigation_id,None,actor_type="system",idempotency_key=f"auto-case:{inv.investigation_id}");created+=1
        db.commit()
    return created

def run_all_tenants(active_tenant_ids,poll_seconds:float=15.0):
    while True:
        for tenant_id in active_tenant_ids():run_tenant_once(tenant_id)
        time.sleep(max(1.0,poll_seconds))

# Authority boundary: this worker may create/cluster cases only. It must never approve/execute remediation,
# place/release payment holds, authorize payments, post journals, close periods, change adjudication, or move funds.
