from __future__ import annotations

import os
import socket
import time

from app.core.config import get_settings
from app.db.session import get_session_factory, set_tenant_context
from app.services.communication_delivery import CommunicationDeliveryService


def run_tenant_once(tenant_id:str,worker_id:str)->dict:
    factory=get_session_factory()
    with factory() as db:
        set_tenant_context(db,tenant_id); svc=CommunicationDeliveryService(db,tenant_id)
        leased=svc.lease(worker_id,limit=50)
        # Persist the lease batch before provider I/O. A crash after this point leaves
        # rows recoverable solely by lease expiry; it never causes claim adjudication.
        db.commit()
        results=[]
        for row in leased:
            try:
                results.append(svc.execute(row.dispatch_id,worker_id)); db.commit()
            except Exception:
                db.rollback()
                # The persisted lease remains until expiry, preventing hot-loop replay.
                # Another worker can recover it after the lease deadline.
                continue
        return {"leased":len(leased),"processed":len(results)}


def run_all_tenants(active_tenant_ids)->None:
    settings=get_settings(); worker_id=f"comm-{socket.gethostname()}-{os.getpid()}"
    while True:
        for tenant_id in active_tenant_ids(): run_tenant_once(tenant_id,worker_id)
        time.sleep(max(0.25,settings.communication_worker_poll_seconds))
