import { NextRequest, NextResponse } from "next/server";
import { backendRequest, ReviewerSessionError } from "@/lib/server/backend";

export const dynamic = "force-dynamic";

export async function GET(request:NextRequest, context:{params:Promise<{claimId:string;evidenceId:string}>}){
  const {claimId,evidenceId}=await context.params;
  try{
    const access=await backendRequest(`/api/v1/claims/${encodeURIComponent(claimId)}/review/evidence/${encodeURIComponent(evidenceId)}/access`);
    if(!access.ok) return NextResponse.json({error:"evidence_access_denied"},{status:access.status});
    const meta=await access.json() as {url:string;media_type:string;content_sha256:string};
    const headers=new Headers(); const range=request.headers.get("range"); if(range)headers.set("range",range);
    const upstream=await fetch(meta.url,{headers,cache:"no-store",signal:request.signal});
    if(!upstream.ok||!upstream.body)return NextResponse.json({error:"evidence_stream_unavailable"},{status:upstream.status||502});
    const out=new Headers();
    out.set("content-type",upstream.headers.get("content-type")||meta.media_type||"application/octet-stream");
    out.set("cache-control","private, no-store"); out.set("x-content-type-options","nosniff"); out.set("accept-ranges",upstream.headers.get("accept-ranges")||"bytes");
    for(const h of ["content-length","content-range","etag"]){const v=upstream.headers.get(h);if(v)out.set(h,v)}
    return new NextResponse(upstream.body,{status:upstream.status,headers:out});
  }catch(error){
    if(error instanceof ReviewerSessionError)return NextResponse.json({error:"authentication_required"},{status:401});
    return NextResponse.json({error:"evidence_stream_unavailable"},{status:502});
  }
}
