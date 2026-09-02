from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.domain.document_intelligence import CitationAnchor, ExtractionBundle, ExtractionUnit, ExtractionUnitType, RetryPolicy
from app.document_intelligence.normalization import normalized_manifest
from app.document_intelligence.isolation import SubprocessParserExecutor
from app.document_intelligence.processors import ProcessorRouter, UnsupportedMedia
from app.main import app


def test_page_and_timestamp_citation_contracts() -> None:
    page=CitationAnchor(evidence_id="ev-1",page_number=2,bbox=(1,2,3,4))
    ts=CitationAnchor(evidence_id="ev-1",start_ms=100,end_ms=250)
    assert page.page_number == 2
    assert ts.end_ms == 250
    with pytest.raises(ValueError): CitationAnchor(evidence_id="ev-1",page_number=0)
    with pytest.raises(ValueError): CitationAnchor(evidence_id="ev-1",start_ms=10)


def test_extraction_confidence_is_preserved_and_aggregated() -> None:
    units=(
        ExtractionUnit(ExtractionUnitType.TEXT,0,"high",{},.9,CitationAnchor("ev-1",page_number=1)),
        ExtractionUnit(ExtractionUnitType.TEXT,1,"low",{},.5,CitationAnchor("ev-1",page_number=1)),
    )
    bundle=ExtractionBundle("test","1","application/pdf",units)
    assert bundle.aggregate_confidence == .7


def test_normalized_manifest_keeps_provenance() -> None:
    unit=ExtractionUnit(ExtractionUnitType.TABLE,0,None,{"rows":[["A","B"]]},.95,CitationAnchor("ev-source",page_number=4,source_locator={"table":0}))
    payload=json.loads(normalized_manifest(ExtractionBundle("table-parser","2","application/pdf",(unit,)),source_evidence_id="ev-source"))
    assert payload["source_evidence_id"] == "ev-source"
    assert payload["units"][0]["citation"]["page_number"] == 4
    assert payload["units"][0]["citation"]["evidence_id"] == "ev-source"


def test_retry_policy_dead_letters_after_max_attempts() -> None:
    policy=RetryPolicy(max_attempts=3,base_delay_seconds=10,max_delay_seconds=25)
    assert policy.delay_seconds(1)==10
    assert policy.delay_seconds(2)==20
    assert policy.delay_seconds(3)==25
    assert not policy.should_dead_letter(2)
    assert policy.should_dead_letter(3)


def test_processor_router_is_media_specific() -> None:
    pdf,image,audio,video,structured=(object() for _ in range(5))
    router=ProcessorRouter(pdf=pdf,image=image,audio=audio,video=video,structured=structured)
    assert router.select("application/pdf") is pdf
    assert router.select("image/png") is image
    assert router.select("audio/mpeg") is audio
    assert router.select("video/mp4") is video
    assert router.select("application/json") is structured
    with pytest.raises(UnsupportedMedia): router.select("application/octet-stream")


def test_document_intelligence_model_api() -> None:
    client=TestClient(app)
    response=client.get("/api/v1/document-intelligence-model")
    assert response.status_code == 200
    body=response.json()
    assert "isolated_parser" in body["pipeline"]
    assert "timestamp" in " ".join(body["citation_contract"])
    assert "dead_letter_queue" in body["reliability"]


def test_isolated_structured_parser_round_trip() -> None:
    executor=SubprocessParserExecutor(timeout_seconds=10)
    bundle=executor.parse_bytes(b'{"claim":"synthetic","amount":100}',evidence_id="ev-json",media_type="application/json",suffix=".json")
    assert bundle.parser_name == "structured-text"
    assert bundle.units[0].structured_data["json"]["amount"] == 100
    assert bundle.units[0].citation.evidence_id == "ev-json"
