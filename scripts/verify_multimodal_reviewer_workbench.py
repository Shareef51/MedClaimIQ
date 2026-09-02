#!/usr/bin/env python
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from app.domain.multimodal_review import multimodal_reviewer_contract
c=multimodal_reviewer_contract()
assert c['safety']['final_claim_decision_is_human_only'] is True
assert c['safety']['signed_media_access_is_claim_scoped'] is True
required=[
 'backend/app/api/v1/multimodal_review.py','backend/app/services/multimodal_review.py','backend/app/models/multimodal_review.py',
 'backend/alembic/versions/0029_multimodal_reviewer_workbench.py','frontend/components/review/multimodal-investigation.tsx',
 'frontend/app/api/reviewer/claims/[claimId]/evidence/[evidenceId]/content/route.ts','config/multimodal_reviewer_policy.json',
 'docs/MULTIMODAL_REVIEWER_WORKBENCH.md'
]
missing=[x for x in required if not (ROOT/x).exists()]
assert not missing, missing
frontend=(ROOT/'frontend/components/review/multimodal-investigation.tsx').read_text()
for marker in ['Page / image bbox highlight','FHIR resource/version comparison','Jump to cited timecode','Cross-modal inconsistencies','Reviewer annotations']:
    assert marker in frontend, marker
bff=(ROOT/'frontend/app/api/reviewer/claims/[claimId]/evidence/[evidenceId]/content/route.ts').read_text()
assert 'request.headers.get("range")' in bff and 'content-range' in bff
policy=json.loads((ROOT/'config/release_engineering_policy.json').read_text())
assert 'multimodal-reviewer-quality' in policy['gates']['required']
print('multimodal reviewer workbench verifier: PASS')
