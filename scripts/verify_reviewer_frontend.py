from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
required = [
    "frontend/package.json", "frontend/next.config.ts", "frontend/app/review/page.tsx",
    "frontend/app/review/claims/[claimId]/page.tsx", "frontend/components/review/review-queue.tsx",
    "frontend/components/review/claim-workbench.tsx", "frontend/lib/server/session.ts",
    "frontend/lib/server/backend.ts", "frontend/app/api/reviewer/[...path]/route.ts",
    "frontend/app/api/reviewer/queue/events/route.ts", "frontend/app/api/reviewer/claims/[claimId]/events/route.ts",
    "config/reviewer_frontend_policy.json", "docs/REVIEWER_DASHBOARD_FRONTEND.md"
]
missing = [p for p in required if not (ROOT / p).exists()]
assert not missing, missing
package = json.loads((ROOT / "frontend/package.json").read_text())
assert package["dependencies"]["next"].startswith("16.")
assert package["dependencies"]["react"].startswith("19.")
component = (ROOT / "frontend/components/review/claim-workbench.tsx").read_text()
for token in ["Exclusive review lease active", "AI override reason required", "Evidence pack & citations", "Hospital / FHIR cross-verification", "Authoritative evidence graph", "MCP approvals", "SLA countdowns", "Record human decision"]:
    assert token in component, token
session = (ROOT / "frontend/lib/server/session.ts").read_text()
assert "localStorage" not in session and "sessionStorage" not in session
assert "seal(" in session and "httpOnly: true" in session
bff = (ROOT / "frontend/app/api/reviewer/[...path]/route.ts").read_text()
assert "ALLOWED" in bff and "assertSameOrigin" in bff
backend = (ROOT / "backend/app/api/v1/review_workbench.py").read_text()
assert '"/review/queue/events"' in backend and "TenantRealtimeStreamer" in backend
print("reviewer frontend verification: ok")
