import "server-only";

function required(name: string): string {
  const value = process.env[name]?.trim();
  if (!value) throw new Error(`${name} is required`);
  return value;
}

export const serverEnv = {
  backendUrl: () => required("MEDCLAIMIQ_BACKEND_URL").replace(/\/$/, ""),
  frontendOrigin: () => required("MEDCLAIMIQ_FRONTEND_ORIGIN").replace(/\/$/, ""),
  sessionSecret: () => { const value = required("MEDCLAIMIQ_FRONTEND_SESSION_SECRET"); if (value.length < 32) throw new Error("MEDCLAIMIQ_FRONTEND_SESSION_SECRET must be at least 32 characters"); return value; },
  oidcIssuer: () => required("MEDCLAIMIQ_OIDC_ISSUER").replace(/\/$/, ""),
  oidcClientId: () => required("MEDCLAIMIQ_OIDC_CLIENT_ID"),
  oidcClientSecret: () => process.env.MEDCLAIMIQ_OIDC_CLIENT_SECRET?.trim() || undefined,
  oidcScope: () => process.env.MEDCLAIMIQ_OIDC_SCOPE?.trim() || "openid profile email offline_access medclaimiq.api",
  oidcClientAuthMethod: () => process.env.MEDCLAIMIQ_OIDC_CLIENT_AUTH_METHOD?.trim() || "client_secret_post",
  defaultTenantId: () => process.env.MEDCLAIMIQ_DEFAULT_TENANT_ID?.trim() || "",
  allowDemoSession: () => process.env.NODE_ENV !== "production" && process.env.MEDCLAIMIQ_ALLOW_DEMO_SESSION === "true",
  demoBearerToken: () => process.env.MEDCLAIMIQ_DEMO_BEARER_TOKEN?.trim() || "",
  demoTenantId: () => process.env.MEDCLAIMIQ_DEMO_TENANT_ID?.trim() || process.env.MEDCLAIMIQ_DEFAULT_TENANT_ID?.trim() || "",
  demoPersonaToken: (persona: string) => {
    if (!serverEnv.allowDemoSession()) return "";
    const map: Record<string,string|undefined> = {
      claims_reviewer: process.env.MEDCLAIMIQ_DEMO_REVIEWER_TOKEN || process.env.MEDCLAIMIQ_DEMO_BEARER_TOKEN,
      tenant_admin: process.env.MEDCLAIMIQ_DEMO_ADMIN_TOKEN,
      auditor: process.env.MEDCLAIMIQ_DEMO_AUDITOR_TOKEN,
      finance_analyst: process.env.MEDCLAIMIQ_DEMO_FINANCE_TOKEN,
      provider: process.env.MEDCLAIMIQ_DEMO_PROVIDER_TOKEN,
      patient: process.env.MEDCLAIMIQ_DEMO_PATIENT_TOKEN,
    };
    return map[persona]?.trim() || "";
  }
};
