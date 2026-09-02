import { NextRequest, NextResponse } from "next/server";
import { serverEnv } from "@/lib/server/env";
import { setSession } from "@/lib/server/session";

const allowed = new Set(["claims_reviewer","tenant_admin","auditor","finance_analyst","provider","patient"]);
export async function POST(request:NextRequest){
  if(!serverEnv.allowDemoSession()) return NextResponse.json({detail:"Synthetic demo login is disabled"},{status:404});
  const form=await request.formData(); const persona=String(form.get("persona")||"");
  if(!allowed.has(persona)) return NextResponse.redirect(new URL("/login?error=invalid_demo_persona",request.url));
  const token=serverEnv.demoPersonaToken(persona); const tenantId=serverEnv.demoTenantId();
  if(!token||!tenantId) return NextResponse.redirect(new URL("/login?error=demo_persona_not_configured",request.url));
  await setSession({access_token:token,token_type:"Bearer",expires_in:3600},tenantId);
  return NextResponse.redirect(new URL(["patient","provider"].includes(persona)?"/portal":"/review",request.url));
}
