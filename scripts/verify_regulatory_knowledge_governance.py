from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.domain.regulatory_knowledge_governance import KNOWLEDGE_GOVERNANCE_AUTHORITY
from app.evaluation.regulatory_knowledge_governance import readiness_score
assert KNOWLEDGE_GOVERNANCE_AUTHORITY["ai_can_publish_authoritative_knowledge"] is False
assert readiness_score({"authoritative_coverage":1,"evidence_freshness":1,"control_lineage_coverage":1,"open_conflict_resolution":1,"historical_finding_coverage":1})["score"] == 100
print("Release 64 regulatory knowledge governance verification: PASS")
