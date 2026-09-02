from pathlib import Path

REQUIRED = [
    "backend/app/domain/access.py",
    "backend/app/services/authorization.py",
    "backend/app/api/v1/access_model.py",
    "backend/tests/test_authorization.py",
    "docs/IDENTITY_AND_ACCESS.md",
    "docs/architecture_decisions/ADR-002-multi-tenant-access-control.md",
    "config/access_control_policy.json",
]

root = Path(__file__).resolve().parents[1]
missing = [path for path in REQUIRED if not (root / path).exists()]
if missing:
    raise SystemExit("Missing access-control files: " + ", ".join(missing))
print("MedClaimIQ access-control structure verified.")
