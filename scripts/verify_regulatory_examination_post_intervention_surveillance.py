from pathlib import Path
required=[
"backend/app/domain/regulatory_examination_post_intervention_surveillance.py",
"backend/app/evaluation/regulatory_examination_post_intervention_surveillance.py",
"backend/app/schemas/regulatory_examination_post_intervention_surveillance.py",
"backend/app/services/regulatory_examination_post_intervention_surveillance.py",
"backend/app/api/v1/regulatory_examination_post_intervention_surveillance.py",
"backend/app/workers/regulatory_examination_post_intervention_surveillance.py",
"backend/alembic/versions/0071_reg_exam_post_intervention_surveillance.py",
"config/regulatory-post-intervention-surveillance-policy.json",
"docs/regulatory-examination-post-intervention-surveillance.md",
]
missing=[x for x in required if not Path(x).exists()]
assert not missing, missing
text=Path(required[0]).read_text()
for token in ["ai_can_reopen_intervention_program\": False","human_reopening_approval_required\": True","payment_authority_allowed\": False"]: assert token in text, token
print("Release 76 verification passed")
