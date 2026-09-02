import { NextRequest, NextResponse } from "next/server";
import { assertSameOrigin, backendRequest, ReviewerSessionError } from "@/lib/server/backend";

const ALLOWED = [
  /^review\/queue(?:\/refresh)?$/,
  /^claims\/[A-Za-z0-9_.:-]+\/review\/(?:workbench|lock|lock\/renew|begin|notes|request-evidence|decision|multimodal|multimodal\/annotations)$/,
  /^claims\/[A-Za-z0-9_.:-]+\/review\/evidence\/[A-Za-z0-9_.:-]+\/(?:access|page-preview)$/,
  /^claims\/[A-Za-z0-9_.:-]+\/mcp\/approvals\/[A-Za-z0-9_.:-]+\/decision$/,
  /^claims\/[A-Za-z0-9_.:-]+\/review\/governed-closure(?:\/traceability|\/packets(?:\/[A-Za-z0-9_.:-]+\/(?:validate|second-review|close))?)?$/,
  /^claims\/[A-Za-z0-9_.:-]+\/post-decision(?:\/notices\/[A-Za-z0-9_.:-]+\/release|\/appeals\/[A-Za-z0-9_.:-]+\/(?:assign|reopen))?$/,
  /^claims\/[A-Za-z0-9_.:-]+\/communications\/(?:notices\/[A-Za-z0-9_.:-]+\/(?:queue|reconcile)|traceability)$/,
  /^communications\/operations\/dashboard$/,
  /^claims\/[A-Za-z0-9_.:-]+\/appeals\/[A-Za-z0-9_.:-]+\/reconsideration(?:\/snapshot|\/reingest|\/search|\/agent-run|\/annotations|\/missing-evidence|\/escalate|\/checkpoints\/[A-Za-z0-9_.:-]+\/resume)?$/,
  /^claims\/[A-Za-z0-9_.:-]+\/appeals\/[A-Za-z0-9_.:-]+\/resolution(?:\/packet|\/packets\/[A-Za-z0-9_.:-]+\/(?:lock|second-review|close)|\/notices\/[A-Za-z0-9_.:-]+\/release)?$/,
  /^claims\/[A-Za-z0-9_.:-]+\/financial-handoff(?:\/traceability|\/packet|\/packets\/[A-Za-z0-9_.:-]+\/(?:lock|authorize|payment-intent)|\/holds(?:\/[A-Za-z0-9_.:-]+\/release)?|\/payment-intents\/[A-Za-z0-9_.:-]+\/(?:handoff|settlement|void-reissue)|\/void-reissue\/[A-Za-z0-9_.:-]+\/approve)?$/,
  /^claims\/[A-Za-z0-9_.:-]+\/accounting-ledger(?:\/traceability|\/payment-intents\/[A-Za-z0-9_.:-]+\/(?:era|eft|reconcile|returns|adjustments)|\/adjustments\/[A-Za-z0-9_.:-]+\/approve)?$/,
  /^accounting-ledger\/(?:periods\/[A-Za-z0-9_.:-]+\/close|aging\/refresh)$/,
  /^claims\/[A-Za-z0-9_.:-]+\/financial-intelligence(?:\/investigations)?$/,
  /^financial-intelligence\/(?:portfolio|copilot)$/,
  /^financial-investigations(?:\/.*)?$/,
  /^recovery-operations(?:\/.*)?$/,
  /^provider-dispute-intelligence(?:\/.*)?$/,
  /^recovery-settlements(?:\/.*)?$/,
  /^recovery-settlement-intelligence(?:\/.*)?$/,
  /^recovery-control-assurance(?:\/.*)?$/,
  /^regulatory-transport(?:\/.*)?$/,
  /^regulatory-supervision(?:\/.*)?$/,
  /^regulatory-examinations(?:\/.*)?$/,
  /^regulatory-remediation(?:\/.*)?$/,
  /^regulatory-portfolio-oversight(?:\/.*)?$/,
  /^claims\/[A-Za-z0-9_.:-]+\/sla\/countdowns$/,
  /^llmops\/summary$/,
  /^llmops\/slos\/evaluate$/,
  /^llmops\/traces\/[A-Fa-f0-9]{16,64}$/
];

function isAllowed(path: string) {
  return ALLOWED.some((pattern) => pattern.test(path));
}

async function proxy(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  const joined = path.join("/");
  if (!isAllowed(joined)) return NextResponse.json({ error: "reviewer_route_not_allowed" }, { status: 404 });
  try { assertSameOrigin(request); } catch { return NextResponse.json({ error: "origin_rejected" }, { status: 403 }); }

  const target = new URL(`/api/v1/${joined}`, "http://internal");
  request.nextUrl.searchParams.forEach((value, key) => target.searchParams.append(key, value));
  const headers = new Headers();
  for (const name of ["content-type", "idempotency-key", "x-review-lock-token", "traceparent"]) {
    const value = request.headers.get(name);
    if (value) headers.set(name, value);
  }
  const body = ["GET", "HEAD"].includes(request.method) ? undefined : await request.text();

  try {
    const upstream = await backendRequest(`${target.pathname}${target.search}`, {
      method: request.method,
      headers,
      body
    });
    const responseHeaders = new Headers();
    responseHeaders.set("content-type", upstream.headers.get("content-type") || "application/json");
    responseHeaders.set("cache-control", "no-store");
    return new NextResponse(upstream.body, { status: upstream.status, headers: responseHeaders });
  } catch (error) {
    if (error instanceof ReviewerSessionError) return NextResponse.json({ error: "authentication_required" }, { status: 401 });
    return NextResponse.json({ error: "backend_unavailable" }, { status: 502 });
  }
}

export const GET = proxy;
export const POST = proxy;
export const DELETE = proxy;
