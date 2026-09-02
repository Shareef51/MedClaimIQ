from __future__ import annotations
import json, subprocess, sys, tempfile
from pathlib import Path
from app.domain.document_intelligence import CitationAnchor, ExtractionBundle, ExtractionUnit, ExtractionUnitType


class ParserIsolationError(RuntimeError): pass


class SubprocessParserExecutor:
    """Runs parser code in a separate OS process with a hard wall-clock timeout.

    Container/Kubernetes deployments should additionally apply seccomp/AppArmor, read-only FS,
    no network, CPU/memory limits and a non-root UID to the parser worker container.
    """
    def __init__(self, timeout_seconds: int = 120): self.timeout_seconds=timeout_seconds
    def parse_bytes(self, content: bytes, *, evidence_id: str, media_type: str, suffix: str) -> ExtractionBundle:
        with tempfile.TemporaryDirectory(prefix="medclaimiq-parser-") as tmp:
            src=Path(tmp)/f"input{suffix}"; out=Path(tmp)/"result.json"; src.write_bytes(content)
            command=[sys.executable,"-m","app.document_intelligence.parser_worker","--input",str(src),"--output",str(out),"--evidence-id",evidence_id,"--media-type",media_type]
            try:
                completed=subprocess.run(command,capture_output=True,text=True,timeout=self.timeout_seconds,check=False)
            except subprocess.TimeoutExpired as exc: raise ParserIsolationError("parser_timeout") from exc
            if completed.returncode != 0: raise ParserIsolationError(f"parser_failed:{completed.stderr[-500:]}")
            return bundle_from_dict(json.loads(out.read_text(encoding="utf-8")))


def bundle_from_dict(data: dict) -> ExtractionBundle:
    units=[]
    for item in data["units"]:
        c=item["citation"]
        units.append(ExtractionUnit(ExtractionUnitType(item["unit_type"]),int(item["sequence"]),item.get("text"),item.get("structured_data",{}),float(item["confidence"]),CitationAnchor(evidence_id=c["evidence_id"],page_number=c.get("page_number"),start_ms=c.get("start_ms"),end_ms=c.get("end_ms"),bbox=tuple(c["bbox"]) if c.get("bbox") else None,frame_index=c.get("frame_index"),frame_sha256=c.get("frame_sha256"),source_locator=c.get("source_locator",{}))))
    return ExtractionBundle(data["parser_name"],data["parser_version"],data["media_type"],tuple(units),tuple(data.get("warnings",[])),data.get("metadata",{}))
