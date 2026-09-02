from fastapi import APIRouter

router=APIRouter(tags=["document-intelligence"])

@router.get("/document-intelligence-model")
def document_intelligence_model() -> dict[str, object]:
    return {
        "pipeline": ["accepted_evidence","isolated_parser","normalized_units","derived_evidence","lineage","processing_event"],
        "media": {"pdf":["layout_text","tables","page_bbox"],"image":["ocr","bbox"],"audio":["transcript_segments","timestamps"],"video":["transcript_segments","keyframes","timestamps"],"structured":["json","csv"]},
        "citation_contract": ["source_evidence_id","page_number_or_timestamp","bbox_when_available","source_locator"],
        "reliability": ["idempotent_runs","exponential_retry","dead_letter_queue","parser_timeout","tenant_rls"],
        "provenance": "Every normalized/derived output preserves a DERIVED_FROM lineage edge to the accepted source evidence.",
        "security": "Parsers execute outside the API process; deployment profiles should additionally deny network and enforce non-root/resource limits.",
    }
