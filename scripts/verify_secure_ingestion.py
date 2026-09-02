from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

checks = {
    "upload persistence": ROOT / "backend/app/models/ingestion.py",
    "storage adapter": ROOT / "backend/app/storage/object_store.py",
    "content validator": ROOT / "backend/app/ingestion/content_validation.py",
    "malware scanner": ROOT / "backend/app/ingestion/malware.py",
    "ingestion service": ROOT / "backend/app/services/ingestion.py",
    "quarantine worker": ROOT / "backend/app/workers/evidence_ingestion.py",
    "API": ROOT / "backend/app/api/v1/ingestion.py",
    "migration": ROOT / "backend/alembic/versions/0004_secure_multimodal_ingestion.py",
    "policy": ROOT / "config/evidence_ingestion_policy.json",
}
for name, path in checks.items():
    if not path.exists():
        raise SystemExit(f"missing {name}: {path}")

storage = checks["storage adapter"].read_text(encoding="utf-8")
worker = checks["quarantine worker"].read_text(encoding="utf-8")
model = checks["upload persistence"].read_text(encoding="utf-8")
migration = checks["migration"].read_text(encoding="utf-8")

assert "generate_presigned_post" in storage
assert "content-length-range" in storage
assert "quarantine/" in (ROOT / "backend/app/services/ingestion.py").read_text(encoding="utf-8")
assert "hashlib.sha256" in worker
assert "MalwareVerdict.CLEAN" in worker
assert "promote_object" in worker
assert "client_filename_sha256" in model
assert "original_filename" not in model
assert "ENABLE ROW LEVEL SECURITY" in migration
assert "evidence_processing_events_immutable" in migration
print("Secure multimodal ingestion architecture verified.")
