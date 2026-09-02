from __future__ import annotations
import hashlib, json
from app.domain.document_intelligence import ExtractionBundle


def normalized_manifest(bundle: ExtractionBundle, *, source_evidence_id: str) -> bytes:
    payload={"schema":"medclaimiq.extraction.v1","source_evidence_id":source_evidence_id,"parser":{"name":bundle.parser_name,"version":bundle.parser_version},"media_type":bundle.media_type,"aggregate_confidence":bundle.aggregate_confidence,"warnings":list(bundle.warnings),"metadata":bundle.metadata,"units":[]}
    for unit in bundle.units:
        citation={"evidence_id":unit.citation.evidence_id,"page_number":unit.citation.page_number,"start_ms":unit.citation.start_ms,"end_ms":unit.citation.end_ms,"bbox":list(unit.citation.bbox) if unit.citation.bbox else None,"frame_index":unit.citation.frame_index,"frame_sha256":unit.citation.frame_sha256,"source_locator":unit.citation.source_locator}
        payload["units"].append({"unit_type":unit.unit_type.value,"sequence":unit.sequence,"text":unit.text,"structured_data":unit.structured_data,"confidence":unit.confidence,"citation":citation})
    return json.dumps(payload,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")


def unit_hash(text: str | None, structured_data: dict[str, object]) -> str:
    raw=json.dumps({"text":text,"structured_data":structured_data},sort_keys=True,separators=(",",":"),ensure_ascii=False).encode(); return hashlib.sha256(raw).hexdigest()
