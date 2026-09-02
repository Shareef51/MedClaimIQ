from __future__ import annotations
import argparse, json
from dataclasses import asdict
from pathlib import Path
from app.document_intelligence.processors import ProcessorRouter


def main() -> int:
    p=argparse.ArgumentParser(); p.add_argument("--input",required=True); p.add_argument("--output",required=True); p.add_argument("--evidence-id",required=True); p.add_argument("--media-type",required=True); a=p.parse_args()
    bundle=ProcessorRouter().select(a.media_type).parse(Path(a.input),evidence_id=a.evidence_id,media_type=a.media_type)
    Path(a.output).write_text(json.dumps(asdict(bundle),default=list),encoding="utf-8")
    return 0
if __name__ == "__main__": raise SystemExit(main())
