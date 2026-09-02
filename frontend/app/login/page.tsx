import { FileCheck2, ShieldCheck, Workflow } from "lucide-react";
import { serverEnv } from "@/lib/server/env";

const personas=[
  ["claims_reviewer","Claims reviewer","Review evidence, agents and decisions"],
  ["tenant_admin","Operations administrator","Cross-domain administration and governed operations"],
  ["auditor","Audit & compliance","Regulatory and assurance workbenches"],
  ["finance_analyst","Finance analyst","Financial investigation and recovery intelligence"],
  ["provider","Provider portal","Disputes, documents and claim status"],
  ["patient","Patient portal","Claim status and document response"],
] as const;

export default async function LoginPage({ searchParams }: { searchParams: Promise<{ error?: string }> }) {
  const { error } = await searchParams; const defaultTenant=process.env.MEDCLAIMIQ_DEFAULT_TENANT_ID||""; const demo=serverEnv.allowDemoSession();
  return <main className="min-h-screen grid lg:grid-cols-[1.15fr_.85fr]">
    <section className="hidden lg:flex p-8 xl:p-12 flex-col justify-between border-r border-[#20364e] bg-[#0a1626]/80">
      <div className="flex items-center gap-3"><div className="h-10 w-10 rounded-xl bg-teal-400/15 border border-teal-300/30 grid place-items-center"><ShieldCheck className="h-5 w-5 text-teal-300"/></div><div><div className="font-bold text-lg">MedClaimIQ</div><div className="text-xs text-slate-400">Secure Claims Portal</div></div></div>
      <div className="max-w-xl"><div className="text-xs uppercase tracking-[.2em] text-teal-300 font-bold mb-5">Evidence before action</div><h1 className="text-4xl xl:text-5xl font-semibold tracking-tight leading-[1.04]">Secure claim review and document response for patients, providers, and claims teams.</h1><p className="mt-6 text-lg text-slate-400 leading-8">Your organization identity determines the least-privilege experience available to you. Patient and provider users see claim status and document requests; reviewer-only reasoning remains internal.</p></div>
      <div className="grid grid-cols-2 gap-4 text-sm"><div className="card p-4"><Workflow className="h-5 w-5 text-sky-300 mb-3"/><div className="font-semibold">Durable workflows</div><div className="text-slate-400 mt-1">Human checkpoints, resumable orchestration and audit trails.</div></div><div className="card p-4"><FileCheck2 className="h-5 w-5 text-emerald-300 mb-3"/><div className="font-semibold">Immutable evidence</div><div className="text-slate-400 mt-1">Citations, source versions and decision snapshots.</div></div></div>
    </section>
    <section className="flex items-center justify-center p-4 md:p-6"><div className="w-full max-w-lg card p-6 md:p-7">
      <div className="lg:hidden flex items-center gap-3 mb-8"><ShieldCheck className="text-teal-300"/><span className="font-bold">MedClaimIQ</span></div><h2 className="text-2xl font-bold">Sign in to MedClaimIQ</h2><p className="mt-2 text-sm text-slate-400">Sign in securely with your organization account.</p>
      {error&&<div role="alert" className="mt-5 rounded-xl border border-rose-400/30 bg-rose-950/30 p-3 text-sm text-rose-200">Authentication failed: {error.replaceAll("_"," ")}</div>}
      <form action="/api/auth/login" method="get" className="mt-7 space-y-4"><label className="block"><span className="text-sm font-semibold">Organization ID</span><input className="input mt-2" name="tenant" defaultValue={defaultTenant} placeholder="tenant-demo-payer" required/></label><button className="btn btn-primary w-full py-3" type="submit"><ShieldCheck className="h-4 w-4"/>Continue with enterprise identity</button></form>
      {demo&&<section className="mt-6 border-t border-[#233b55] pt-5"><div className="flex items-center justify-between gap-3"><div><div className="text-sm font-bold">Synthetic recruiter demo</div><p className="text-xs text-slate-500 mt-1">Non-production only. Choose a synthetic role to explore role-specific workflows.</p></div><span className="badge badge-low">Demo only</span></div><div className="grid sm:grid-cols-2 gap-2 mt-4">{personas.map(([value,label,detail])=><form key={value} action="/api/auth/demo" method="post"><input type="hidden" name="persona" value={value}/><button className="w-full text-left rounded-xl border border-[#233b55] p-3 hover:border-teal-400/50 hover:bg-white/5"><span className="block text-sm font-semibold">{label}</span><span className="block text-[11px] text-slate-500 mt-1">{detail}</span></button></form>)}</div></section>}
      <details className="mt-6 text-xs text-slate-500"><summary className="cursor-pointer hover:text-slate-300">Security & privacy details</summary><p className="mt-2 leading-5">Enterprise sign-in uses OIDC Authorization Code + PKCE. Tokens are handled by the Next.js BFF in encrypted HttpOnly cookies and are not stored by browser JavaScript.</p></details>
    </div></section>
  </main>;
}
