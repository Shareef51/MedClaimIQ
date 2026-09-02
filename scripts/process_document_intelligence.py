from __future__ import annotations
import argparse
from app.core.config import get_settings
from app.core.document_intelligence_factory import build_document_intelligence_worker
from app.db.session import get_session_factory


def main() -> int:
    p=argparse.ArgumentParser(description="Process one accepted evidence artifact through document intelligence")
    p.add_argument("--tenant-id",required=True); p.add_argument("--evidence-id",required=True); p.add_argument("--attempt",type=int,default=1); p.add_argument("--trace-id")
    a=p.parse_args(); settings=get_settings(); factory=get_session_factory(settings)
    with factory() as session:
        worker=build_document_intelligence_worker(session,a.tenant_id,settings)
        run=worker.process(a.evidence_id,attempt_number=a.attempt,trace_id=a.trace_id)
        session.commit()
        print({"run_id":run.run_id,"status":run.status,"attempt_number":run.attempt_number,"unit_count":run.unit_count,"derived_evidence_id":run.derived_evidence_id,"error_code":run.error_code})
    return 0
if __name__ == "__main__": raise SystemExit(main())
