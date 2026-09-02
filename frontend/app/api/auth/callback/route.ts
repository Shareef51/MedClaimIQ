import { NextRequest, NextResponse } from "next/server";
import { exchangeCode } from "@/lib/server/oidc";
import { setSession, takeOAuthTransaction } from "@/lib/server/session";
import { serverEnv } from "@/lib/server/env";

export async function GET(request: NextRequest) {
  const error = request.nextUrl.searchParams.get("error");
  if (error) return NextResponse.redirect(new URL(`/login?error=${encodeURIComponent(error)}`, serverEnv.frontendOrigin()));
  const code = request.nextUrl.searchParams.get("code");
  const state = request.nextUrl.searchParams.get("state");
  const txn = await takeOAuthTransaction();
  if (!code || !state || !txn || state !== txn.state) {
    return NextResponse.redirect(new URL("/login?error=invalid_oauth_state", serverEnv.frontendOrigin()));
  }
  try {
    const token = await exchangeCode(code, txn.verifier);
    await setSession(token, txn.tenantId);
    return NextResponse.redirect(new URL("/", serverEnv.frontendOrigin()));
  } catch {
    return NextResponse.redirect(new URL("/login?error=token_exchange_failed", serverEnv.frontendOrigin()));
  }
}
