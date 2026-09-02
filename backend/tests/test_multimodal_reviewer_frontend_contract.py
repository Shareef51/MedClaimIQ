from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]


def test_multimodal_reviewer_frontend_has_visual_and_traceability_surfaces():
    p=ROOT/'frontend/components/review/multimodal-investigation.tsx'
    text=p.read_text()
    assert 'Cross-modal evidence' in text
    assert 'Page / image bbox highlight' in text
    assert 'Jump to cited timecode' in text
    assert 'Jump to cited timecode/frame' in text
    assert 'FHIR resource/version comparison' in text
    assert 'Cross-modal inconsistencies' in text
    assert 'Multimodal agent findings & citation drill-down' in text
    assert 'Durable checkpoint' in text
    assert 'Reviewer annotations' in text


def test_multimodal_media_stays_same_origin_and_range_capable():
    route=(ROOT/'frontend/app/api/reviewer/claims/[claimId]/evidence/[evidenceId]/content/route.ts').read_text()
    component=(ROOT/'frontend/components/review/multimodal-investigation.tsx').read_text()
    assert 'request.headers.get("range")' in route
    assert 'content-range' in route and 'accept-ranges' in route
    assert '/api/reviewer/claims/' in component
    assert 'https://signed' not in component


def test_existing_human_decision_panel_remains_authoritative():
    text=(ROOT/'frontend/components/review/claim-workbench.tsx').read_text()
    assert 'Record human decision' in text
    assert 'AI override reason required' in text
    assert '<MultimodalInvestigation' in text
