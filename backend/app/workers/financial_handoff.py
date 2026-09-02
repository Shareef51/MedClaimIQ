from __future__ import annotations
import os,socket,time
from sqlalchemy import select
from app.db.session import get_session_factory,set_tenant_context
from app.models.financial_handoff import PaymentIntentModel
from app.services.financial_handoff import FinancialHandoffService

def run_tenant_once(tenant_id:str,worker_id:str,limit:int=25)->dict:
    factory=get_session_factory();processed=0
    with factory() as db:
        set_tenant_context(db,tenant_id)
        ids=list(db.scalars(select(PaymentIntentModel.payment_intent_id).where(PaymentIntentModel.tenant_id==tenant_id,PaymentIntentModel.status=="ready_for_handoff").order_by(PaymentIntentModel.created_at).limit(limit)))
    for payment_intent_id in ids:
        with factory() as db:
            set_tenant_context(db,tenant_id);svc=FinancialHandoffService(db,tenant_id)
            try:
                intent=db.get(PaymentIntentModel,payment_intent_id)
                if intent is None: continue
                svc.handoff(intent.claim_id,payment_intent_id,actor_id="financial-handoff-worker",idempotency_key=f"worker-handoff:{payment_intent_id}")
                db.commit();processed+=1
            except Exception:
                db.rollback()
    return {"selected":len(ids),"processed":processed}

def run_all_tenants(active_tenant_ids)->None:
    worker_id=f"financial-{socket.gethostname()}-{os.getpid()}";poll=float(os.getenv("FINANCIAL_HANDOFF_WORKER_POLL_SECONDS","1.0"))
    while True:
        for tenant_id in active_tenant_ids():run_tenant_once(tenant_id,worker_id)
        time.sleep(max(.25,poll))
