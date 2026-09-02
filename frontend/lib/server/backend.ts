import "server-only";
import { getAccessSession, getTenantId } from "./session";
import { serverEnv } from "./env";

export class ReviewerSessionError extends Error {}

export async function backendRequest(path: string, init: RequestInit = {}): Promise<Response> {
  const session = await getAccessSession();
  const tenantId = await getTenantId();
  if (!session || !tenantId) throw new ReviewerSessionError("Reviewer session is not available");

  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${session.accessToken}`);
  headers.set("X-Tenant-Id", tenantId);
  headers.set("Accept", headers.get("Accept") || "application/json");

  return fetch(`${serverEnv.backendUrl()}${path}`, {
    ...init,
    headers,
    cache: "no-store",
    redirect: "manual",
    signal: init.signal ?? AbortSignal.timeout(15_000)
  });
}

export function assertSameOrigin(request: Request) {
  if (["GET", "HEAD", "OPTIONS"].includes(request.method)) return;
  const origin = request.headers.get("origin");
  if (!origin || origin !== serverEnv.frontendOrigin()) {
    throw new Error("Cross-origin mutation rejected");
  }
}
