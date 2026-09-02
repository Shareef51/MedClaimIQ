import { NextRequest, NextResponse } from "next/server";
import { clearSession } from "@/lib/server/session";
import { assertSameOrigin } from "@/lib/server/backend";
import { serverEnv } from "@/lib/server/env";

export async function POST(request: NextRequest) {
  try { assertSameOrigin(request); } catch { return NextResponse.json({ error: "origin_rejected" }, { status: 403 }); }
  await clearSession();
  return NextResponse.redirect(new URL("/login", serverEnv.frontendOrigin()), { status: 303 });
}
