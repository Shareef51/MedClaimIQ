from pathlib import Path
root=Path(__file__).resolve().parents[1]
required=["backend/app/domain/document_intelligence.py","backend/app/models/document_intelligence.py","backend/app/document_intelligence/processors.py","backend/app/document_intelligence/isolation.py","backend/app/workers/document_intelligence.py","backend/alembic/versions/0005_document_intelligence.py","config/document_intelligence_policy.json","docs/MULTIMODAL_DOCUMENT_INTELLIGENCE.md"]
missing=[p for p in required if not (root/p).exists()]
if missing: raise SystemExit(f"missing: {missing}")
text=(root/"backend/alembic/versions/0005_document_intelligence.py").read_text()
for token in ("ENABLE ROW LEVEL SECURITY","FORCE ROW LEVEL SECURITY","_append_only BEFORE UPDATE OR DELETE","extraction_units","extraction_dead_letters"):
    if token not in text: raise SystemExit(f"migration missing {token}")
print("document intelligence architecture: OK")
