from __future__ import annotations

class RegulatoryExaminationReadinessRepository:
    """Repository boundary. The service keeps a deterministic in-process projection for tests/demo; production adapters persist via Release 65 tables."""
    def __init__(self, db, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    def tenant_scope(self, row: dict) -> dict:
        if row.get("tenant_id") not in (None, self.tenant_id):
            raise PermissionError("cross-tenant access denied")
        return {**row, "tenant_id": self.tenant_id}
