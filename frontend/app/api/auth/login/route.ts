import { NextRequest, NextResponse } from "next/server";
import { discoverOIDC, newOAuthState } from "@/lib/server/oidc";
import { setOAuthTransaction } from "@/lib/server/session";
import { serverEnv } from "@/lib/server/env";

export async function GET(request: NextRequest) {
  const tenantId = request.nextUrl.searchParams.get("tenant")?.trim() || serverEnv.defaultTenantId();
  if (!tenantId) return NextResponse.redirect(new URL("/login?error=tenant_required", request.url));

  const discovery = await discoverOIDC();
  const txn = newOAuthState();
  await setOAuthTransaction({ ...txn, tenantId, createdAt: Date.now() });

  const url = new URL(discovery.authorization_endpoint);
  url.searchParams.set("response_type", "code");
  url.searchParams.set("client_id", serverEnv.oidcClientId());
  url.searchParams.set("redirect_uri", `${serverEnv.frontendOrigin()}/api/auth/callback`);
  url.searchParams.set("scope", serverEnv.oidcScope());
  url.searchParams.set("state", txn.state);
  url.searchParams.set("code_challenge", txn.challenge);
  url.searchParams.set("code_challenge_method", "S256");
  return NextResponse.redirect(url);
}
