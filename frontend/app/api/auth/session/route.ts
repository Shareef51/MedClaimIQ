import { NextRequest, NextResponse } from "next/server";
import { backendRequest, ReviewerSessionError } from "@/lib/server/backend";
import { getTenantId } from "@/lib/server/session";

export async function GET() {
  try {
    const response = await backendRequest("/api/v1/auth/me");
    const body = await response.text();
    return new NextResponse(body, {
      status: response.status,
      headers: { "content-type": response.headers.get("content-type") || "application/json", "cache-control": "no-store" }
    });
  } catch (error) {
    if (error instanceof ReviewerSessionError) return NextResponse.json({ authenticated: false }, { status: 401 });
    return NextResponse.json({ error: "session_unavailable", tenant_id: await getTenantId() }, { status: 503 });
  }
}
