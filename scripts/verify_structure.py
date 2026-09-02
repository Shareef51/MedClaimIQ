from pathlib import Path

REQUIRED = [
    "README.md",
    "docs/PRODUCT_SCOPE.md",
    "docs/SAFETY_BOUNDARIES.md",
    "docs/CLAIM_LIFECYCLE.md",
    "backend/app/main.py",
    "backend/app/api/v1/health.py",
    "backend/tests/test_health.py",
    "docker-compose.yml",
]

root = Path(__file__).resolve().parents[1]
missing = [path for path in REQUIRED if not (root / path).exists()]

if missing:
    raise SystemExit(f"Missing required project files: {missing}")

print("MedClaimIQ foundation structure verified.")
