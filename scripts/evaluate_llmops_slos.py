from __future__ import annotations
import argparse
from app.core.config import get_settings
from app.db.session import get_session_factory, set_tenant_context
from app.repositories.llmops import LLMOpsRepository
from app.services.llmops import LLMOpsService

def main():
    p=argparse.ArgumentParser();p.add_argument("--tenant-id",required=True);p.add_argument("--window-minutes",type=int,default=60);args=p.parse_args()
    factory=get_session_factory()
    with factory() as db:
        set_tenant_context(db,args.tenant_id)
        service=LLMOpsService(LLMOpsRepository(db,args.tenant_id),get_settings())
        events=service.evaluate_slos(args.window_minutes)
        db.commit()
        print({"created":len(events),"events":[{"kind":x.slo_kind,"severity":x.severity} for x in events]})
if __name__=="__main__":main()
