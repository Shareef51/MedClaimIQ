from __future__ import annotations

import json
from pathlib import Path

from app.db.session import get_session_factory
from app.schemas.tenancy import MembershipCreate, OrganizationCreate, TenantCreate, UserAccountCreate
from app.services.tenancy import TenancyService


ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "sample-data" / "tenancy_seed.json"


def main() -> None:
    payload = json.loads(SEED.read_text())
    session = get_session_factory()()
    try:
        service = TenancyService(session)
        for item in payload["tenants"]:
            service.create_tenant(TenantCreate(**item))
        for item in payload["organizations"]:
            item = dict(item)
            tenant_id = item.pop("tenant_id")
            service.create_organization(tenant_id, OrganizationCreate(**item))
        for item in payload["users"]:
            service.create_user(UserAccountCreate(**item))
        for item in payload["memberships"]:
            item = dict(item)
            tenant_id = item.pop("tenant_id")
            service.add_membership(tenant_id, MembershipCreate(**item))
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
    print("Synthetic tenancy seed loaded.")


if __name__ == "__main__":
    main()
