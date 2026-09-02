import "server-only";
import { cookies } from "next/headers";
import { seal, unseal } from "./crypto";
import { refreshAccessToken, type TokenResponse } from "./oidc";
import { serverEnv } from "./env";

const COOKIE_PREFIX = process.env.NODE_ENV === "production" ? "__Host-" : "";
const ACCESS_COOKIE = `${COOKIE_PREFIX}medclaimiq_access`;
const REFRESH_COOKIE = `${COOKIE_PREFIX}medclaimiq_refresh`;
const TENANT_COOKIE = `${COOKIE_PREFIX}medclaimiq_tenant`;
const OAUTH_COOKIE = `${COOKIE_PREFIX}medclaimiq_oauth`;

export type AccessSession = {
  accessToken: string;
  expiresAt: number;
};

type OAuthTransaction = {
  state: string;
  verifier: string;
  tenantId: string;
  createdAt: number;
};

function cookieOptions(maxAge: number) {
  return {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax" as const,
    path: "/",
    maxAge
  };
}

export async function setOAuthTransaction(value: OAuthTransaction) {
  const jar = await cookies();
  jar.set(OAUTH_COOKIE, seal(value), cookieOptions(600));
}

export async function takeOAuthTransaction(): Promise<OAuthTransaction | null> {
  const jar = await cookies();
  const value = unseal<OAuthTransaction>(jar.get(OAUTH_COOKIE)?.value);
  jar.delete(OAUTH_COOKIE);
  if (!value || Date.now() - value.createdAt > 10 * 60 * 1000) return null;
  return value;
}

export async function setSession(token: TokenResponse, tenantId: string) {
  const jar = await cookies();
  const expiresIn = Math.max(60, token.expires_in ?? 3600);
  const access: AccessSession = {
    accessToken: token.access_token,
    expiresAt: Date.now() + expiresIn * 1000
  };
  jar.set(ACCESS_COOKIE, seal(access), cookieOptions(expiresIn));
  jar.set(TENANT_COOKIE, seal({ tenantId }), cookieOptions(12 * 60 * 60));
  if (token.refresh_token) {
    jar.set(REFRESH_COOKIE, seal({ refreshToken: token.refresh_token }), cookieOptions(30 * 24 * 60 * 60));
  }
}

export async function clearSession() {
  const jar = await cookies();
  jar.delete(ACCESS_COOKIE);
  jar.delete(REFRESH_COOKIE);
  jar.delete(TENANT_COOKIE);
  jar.delete(OAUTH_COOKIE);
}

export async function getTenantId(): Promise<string | null> {
  const jar = await cookies();
  const tenant = unseal<{ tenantId: string }>(jar.get(TENANT_COOKIE)?.value);
  if (tenant?.tenantId) return tenant.tenantId;
  if (serverEnv.allowDemoSession()) return serverEnv.demoTenantId() || null;
  return null;
}

export async function getAccessSession({ allowRefresh = true } = {}): Promise<AccessSession | null> {
  const jar = await cookies();
  const access = unseal<AccessSession>(jar.get(ACCESS_COOKIE)?.value);
  if (access?.accessToken && access.expiresAt > Date.now() + 60_000) return access;

  if (allowRefresh) {
    const refresh = unseal<{ refreshToken: string }>(jar.get(REFRESH_COOKIE)?.value);
    const tenantId = await getTenantId();
    if (refresh?.refreshToken && tenantId) {
      try {
        const token = await refreshAccessToken(refresh.refreshToken);
        await setSession({ ...token, refresh_token: token.refresh_token ?? refresh.refreshToken }, tenantId);
        return {
          accessToken: token.access_token,
          expiresAt: Date.now() + Math.max(60, token.expires_in ?? 3600) * 1000
        };
      } catch {
        await clearSession();
        return null;
      }
    }
  }

  if (serverEnv.allowDemoSession()) {
    const token = serverEnv.demoBearerToken();
    if (token) return { accessToken: token, expiresAt: Date.now() + 5 * 60 * 1000 };
  }
  return null;
}

export async function hasReviewerSession(): Promise<boolean> {
  return Boolean((await getAccessSession({ allowRefresh: false })) && (await getTenantId()));
}
