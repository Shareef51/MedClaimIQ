from __future__ import annotations
import argparse
from app.db.session import get_session_factory
from app.services.review_workbench import ReviewWorkbenchService

def main():
    ap=argparse.ArgumentParser(description="Refresh persisted human review priority queue for one tenant")
    ap.add_argument("--tenant-id", required=True)
    args=ap.parse_args()
    with get_session_factory()() as db:
        rows=ReviewWorkbenchService(db,args.tenant_id).refresh_queue(); db.commit()
        print(f"refreshed {len(rows)} review work items")
if __name__ == "__main__": main()
