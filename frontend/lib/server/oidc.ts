import "server-only";
import { createHash, randomBytes } from "node:crypto";
import { serverEnv } from "./env";

export type OIDCDiscovery = {
  authorization_endpoint: string;
  token_endpoint: string;
  end_session_endpoint?: string;
};

export type TokenResponse = {
  access_token: string;
  token_type: string;
  expires_in?: number;
  refresh_token?: string;
  scope?: string;
  id_token?: string;
};

let discoveryCache: { value: OIDCDiscovery; expiresAt: number } | null = null;

export async function discoverOIDC(): Promise<OIDCDiscovery> {
  if (discoveryCache && discoveryCache.expiresAt > Date.now()) return discoveryCache.value;
  const issuer = serverEnv.oidcIssuer();
  if (process.env.NODE_ENV === "production" && !issuer.startsWith("https://")) throw new Error("Production OIDC issuer must use HTTPS");
  const response = await fetch(`${issuer}/.well-known/openid-configuration`, {
    cache: "no-store",
    signal: AbortSignal.timeout(7000)
  });
  if (!response.ok) throw new Error(`OIDC discovery failed (${response.status})`);
  const body = (await response.json()) as Partial<OIDCDiscovery>;
  if (!body.authorization_endpoint || !body.token_endpoint) {
    throw new Error("OIDC discovery is missing authorization/token endpoints");
  }
  const value: OIDCDiscovery = {
    authorization_endpoint: body.authorization_endpoint,
    token_endpoint: body.token_endpoint,
    end_session_endpoint: body.end_session_endpoint
  };
  discoveryCache = { value, expiresAt: Date.now() + 5 * 60 * 1000 };
  return value;
}

export function newOAuthState() {
  const verifier = randomBytes(48).toString("base64url");
  const challenge = createHash("sha256").update(verifier).digest("base64url");
  return {
    state: randomBytes(32).toString("base64url"),
    verifier,
    challenge
  };
}

export async function exchangeCode(code: string, verifier: string): Promise<TokenResponse> {
  const discovery = await discoverOIDC();
  const body = new URLSearchParams({
    grant_type: "authorization_code",
    code,
    redirect_uri: `${serverEnv.frontendOrigin()}/api/auth/callback`,
    client_id: serverEnv.oidcClientId(),
    code_verifier: verifier
  });
  const headers = new Headers({ "content-type": "application/x-www-form-urlencoded" });
  const clientSecret = serverEnv.oidcClientSecret();
  const method = serverEnv.oidcClientAuthMethod();
  if (clientSecret && method === "client_secret_basic") {
    headers.set("Authorization", `Basic ${Buffer.from(`${serverEnv.oidcClientId()}:${clientSecret}`).toString("base64")}`);
  } else if (clientSecret) {
    body.set("client_secret", clientSecret);
  }
  const response = await fetch(discovery.token_endpoint, {
    method: "POST",
    body,
    headers,
    cache: "no-store",
    signal: AbortSignal.timeout(7000)
  });
  if (!response.ok) throw new Error(`OIDC token exchange failed (${response.status})`);
  const token = (await response.json()) as Partial<TokenResponse>;
  if (!token.access_token || !token.token_type) throw new Error("OIDC token response is incomplete");
  return token as TokenResponse;
}

export async function refreshAccessToken(refreshToken: string): Promise<TokenResponse> {
  const discovery = await discoverOIDC();
  const body = new URLSearchParams({
    grant_type: "refresh_token",
    refresh_token: refreshToken,
    client_id: serverEnv.oidcClientId()
  });
  const headers = new Headers({ "content-type": "application/x-www-form-urlencoded" });
  const clientSecret = serverEnv.oidcClientSecret();
  const method = serverEnv.oidcClientAuthMethod();
  if (clientSecret && method === "client_secret_basic") {
    headers.set("Authorization", `Basic ${Buffer.from(`${serverEnv.oidcClientId()}:${clientSecret}`).toString("base64")}`);
  } else if (clientSecret) {
    body.set("client_secret", clientSecret);
  }
  const response = await fetch(discovery.token_endpoint, {
    method: "POST",
    body,
    headers,
    cache: "no-store",
    signal: AbortSignal.timeout(7000)
  });
  if (!response.ok) throw new Error(`OIDC refresh failed (${response.status})`);
  const token = (await response.json()) as Partial<TokenResponse>;
  if (!token.access_token || !token.token_type) throw new Error("OIDC refresh response is incomplete");
  return token as TokenResponse;
}
