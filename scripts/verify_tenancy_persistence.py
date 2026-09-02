from pathlib import Path

REQUIRED = [
    "backend/app/db/base.py",
    "backend/app/db/session.py",
    "backend/app/models/tenancy.py",
    "backend/app/repositories/tenancy.py",
    "backend/app/services/tenancy.py",
    "backend/app/schemas/tenancy.py",
    "backend/app/api/v1/tenancy_model.py",
    "backend/alembic.ini",
    "backend/alembic/versions/0001_enterprise_tenancy.py",
    "backend/tests/test_tenancy_persistence.py",
    "backend/tests/test_rls_migration_contract.py",
    "docs/TENANCY_PERSISTENCE.md",
    "docs/architecture_decisions/ADR-003-tenant-persistence-and-database-isolation.md",
    "sample-data/tenancy_seed.json",
]

root = Path(__file__).resolve().parents[1]
missing = [path for path in REQUIRED if not (root / path).exists()]
if missing:
    raise SystemExit("Missing tenancy persistence files: " + ", ".join(missing))
print("MedClaimIQ tenancy persistence structure verified.")
