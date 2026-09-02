import { NextRequest, NextResponse } from "next/server";
import { backendRequest, ReviewerSessionError } from "@/lib/server/backend";

export const dynamic = "force-dynamic";

export async function GET(request: NextRequest) {
  const after = request.nextUrl.searchParams.get("after_sequence") || "0";
  try {
    const upstream = await backendRequest(`/api/v1/review/queue/events?after_sequence=${encodeURIComponent(after)}`, {
      headers: { Accept: "text/event-stream" },
      signal: request.signal
    });
    if (!upstream.ok || !upstream.body) return NextResponse.json({ error: "upstream_stream_unavailable" }, { status: upstream.status || 502 });
    return new NextResponse(upstream.body, {
      status: 200,
      headers: {
        "content-type": "text/event-stream",
        "cache-control": "no-cache, no-store",
        connection: "keep-alive",
        "x-accel-buffering": "no"
      }
    });
  } catch (error) {
    if (error instanceof ReviewerSessionError) return NextResponse.json({ error: "authentication_required" }, { status: 401 });
    return NextResponse.json({ error: "stream_unavailable" }, { status: 502 });
  }
}
