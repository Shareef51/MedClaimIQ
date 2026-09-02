#!/usr/bin/env python
import json,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(root/"backend"))
from app.domain.multimodal_agent_orchestration import multimodal_agent_orchestration_contract
c=multimodal_agent_orchestration_contract()
required={"hospital_verification","invoice_verification","fraud_waste","evidence_fusion","critic","decision_support"}
assert required.issubset(set(c["multimodal_agents"]))
assert (root/"backend/alembic/versions/0028_multimodal_agent_orchestration.py").exists()
assert (root/"config/multimodal_agent_orchestration_policy.json").exists()
assert "multimodal-agent-quality" in json.loads((root/"config/release_engineering_policy.json").read_text())["gates"]["required"]
print("multimodal agent orchestration verifier: PASS")
