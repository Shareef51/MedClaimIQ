import { NextRequest, NextResponse } from "next/server";
import { backendRequest, ReviewerSessionError } from "@/lib/server/backend";
export async function GET(request: NextRequest, context: { params: Promise<{ claimId: string }> }) {
  const { claimId } = await context.params; const after=request.nextUrl.searchParams.get("after_sequence")||"0";
  try {
    const upstream=await backendRequest(`/api/v1/portal/claims/${encodeURIComponent(claimId)}/events?after_sequence=${encodeURIComponent(after)}`,{headers:{Accept:"text/event-stream"},signal:request.signal});
    return new NextResponse(upstream.body,{status:upstream.status,headers:{"content-type":"text/event-stream","cache-control":"no-cache, no-store","x-accel-buffering":"no"}});
  } catch(error) {
    if(error instanceof ReviewerSessionError) return NextResponse.json({error:"authentication_required"},{status:401});
    return NextResponse.json({error:"backend_unavailable"},{status:502});
  }
}
