import { NextRequest, NextResponse } from "next/server";
import { assertSameOrigin, backendRequest, ReviewerSessionError } from "@/lib/server/backend";

const ALLOWED = [
  /^portal\/claims$/,
  /^portal\/claims\/[A-Za-z0-9_.:-]+$/,
  /^portal\/claims\/[A-Za-z0-9_.:-]+\/requests\/[A-Za-z0-9_.:-]+\/uploads$/,
  /^portal\/claims\/[A-Za-z0-9_.:-]+\/requests\/[A-Za-z0-9_.:-]+\/uploads\/[A-Za-z0-9_.:-]+\/complete$/,
  /^portal\/claims\/[A-Za-z0-9_.:-]+\/submissions\/[A-Za-z0-9_.:-]+$/,
  /^portal\/provider-disputes$/,
  /^portal\/recovery-settlements(?:\/[A-Za-z0-9_.:-]+(?:\/(?:evidence|correspondence))?)?$/,
  /^portal\/recovery-balance-statements$/,
  /^portal\/recovery-operations\/[A-Za-z0-9_.:-]+\/disputes\/[A-Za-z0-9_.:-]+\/intelligence(?:\/evidence|\/provider-response)?$/
];
function isAllowed(path: string) { return ALLOWED.some((p) => p.test(path)); }
async function proxy(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params; const joined = `portal/${path.join("/")}`;
  if (!isAllowed(joined)) return NextResponse.json({ error: "portal_route_not_allowed" }, { status: 404 });
  try { assertSameOrigin(request); } catch { return NextResponse.json({ error: "origin_rejected" }, { status: 403 }); }
  const target = new URL(`/api/v1/${joined}`, "http://internal");
  request.nextUrl.searchParams.forEach((v,k) => target.searchParams.append(k,v));
  const headers = new Headers();
  for (const name of ["content-type","idempotency-key","x-trace-id","traceparent"]) { const v=request.headers.get(name); if(v) headers.set(name,v); }
  const body=["GET","HEAD"].includes(request.method)?undefined:await request.text();
  try {
    const upstream=await backendRequest(`${target.pathname}${target.search}`,{method:request.method,headers,body});
    return new NextResponse(upstream.body,{status:upstream.status,headers:{"content-type":upstream.headers.get("content-type")||"application/json","cache-control":"no-store"}});
  } catch(error) {
    if(error instanceof ReviewerSessionError) return NextResponse.json({error:"authentication_required"},{status:401});
    return NextResponse.json({error:"backend_unavailable"},{status:502});
  }
}
export const GET=proxy; export const POST=proxy;
