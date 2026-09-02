from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"backend"))
from app.evaluation.regulatory_examination_response_harness import evaluate_release66
r=evaluate_release66(); print(r)
if not r["passed"]: raise SystemExit(1)
print("Release 66 verification passed")
