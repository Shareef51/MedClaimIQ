from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"backend"))
from app.domain.ai_change_management import sha256_json

def main() -> int:
    parser = argparse.ArgumentParser(description="Compare an expected MedClaimIQ AI configuration payload with an observed payload.")
    parser.add_argument("--expected", required=True)
    parser.add_argument("--observed", required=True)
    args = parser.parse_args()
    expected = json.loads(Path(args.expected).read_text())
    observed = json.loads(Path(args.observed).read_text())
    expected_sha, observed_sha = sha256_json(expected), sha256_json(observed)
    result = {"status": "in_sync" if expected_sha == observed_sha else "drift_detected", "expected_sha256": expected_sha, "observed_sha256": observed_sha}
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "in_sync" else 2

if __name__ == "__main__":
    raise SystemExit(main())
