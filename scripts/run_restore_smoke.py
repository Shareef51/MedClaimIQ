from __future__ import annotations
import hashlib, json, os
from pathlib import Path
from sqlalchemy import create_engine, text

ROOT=Path(__file__).resolve().parents[1]

def main() -> None:
    url=os.environ.get("DATABASE_URL")
    if not url: raise SystemExit("DATABASE_URL is required for restore verification")
    engine=create_engine(url)
    report={"database":{},"object_sample":None,"decision":"PASS","failures":[]}
    with engine.connect() as conn:
        version=conn.execute(text("select version_num from alembic_version")).scalar_one()
        tenants=conn.execute(text("select count(*) from tenants")).scalar_one()
        claims=conn.execute(text("select count(*) from claims")).scalar_one()
        evidence=conn.execute(text("select count(*) from evidence_artifacts")).scalar_one()
        report["database"]={"alembic_version":version,"tenant_count":tenants,"claim_count":claims,"evidence_count":evidence}
        expected=os.environ.get("RESTORE_EXPECTED_ALEMBIC_VERSION","0021_security_privacy_devsecops")
        if version != expected: report["failures"].append(f"alembic version {version} != {expected}")
        sample=conn.execute(text("select object_key, content_sha256, byte_size from evidence_artifacts where status in ('accepted','ready') and object_key is not null order by created_at desc limit 1")).mappings().first()
    if os.environ.get("RESTORE_VERIFY_OBJECT_SAMPLE","false").lower()=="true" and sample:
        from app.core.config import get_settings
        from app.core.ingestion_factory import build_object_storage
        settings=get_settings(); storage=build_object_storage(settings); digest=hashlib.sha256(); size=0
        for chunk in storage.iter_object_chunks(bucket=settings.s3_bucket,key=sample['object_key']): digest.update(chunk); size+=len(chunk)
        ok=digest.hexdigest()==sample['content_sha256'] and size==sample['byte_size']
        report["object_sample"]={"object_key":sample['object_key'],"sha256_matches":digest.hexdigest()==sample['content_sha256'],"size_matches":size==sample['byte_size']}
        if not ok: report["failures"].append("representative evidence object provenance mismatch")
    if report["failures"]: report["decision"]="BLOCK"
    out=ROOT/'artifacts/infrastructure'; out.mkdir(parents=True,exist_ok=True); (out/'restore-smoke.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    if report["failures"]: raise SystemExit(1)
if __name__=='__main__': main()
