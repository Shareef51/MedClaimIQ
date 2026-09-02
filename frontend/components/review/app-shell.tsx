"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import {
  Activity, BadgeDollarSign, Banknote, BookOpenCheck, Bot, ClipboardCheck, FileSearch2, Gauge, LayoutDashboard,
  LogOut, MailCheck, Menu, RefreshCcw, Scale, ShieldAlert, ShieldCheck, Stethoscope, UserRound, X
} from "lucide-react";
import { reviewerApi } from "@/lib/api";
import type { ReviewerSession } from "@/lib/schemas";

type NavItem = { href:string; label:string; icon:React.ComponentType<{className?:string}>; roles?:string[] };
type NavGroup = { label:string; items:NavItem[] };
const financeRoles=["finance_operator","finance_analyst","finance_approver","accounting_controller","auditor","tenant_admin"];
const regulatoryRoles=["auditor","tenant_admin","accounting_controller"];
const nav:NavGroup[]=[
  {label:"Workspace",items:[
    {href:"/review",label:"Overview",icon:LayoutDashboard},
    {href:"/review/claims",label:"Claims",icon:Stethoscope},
    {href:"/review/appeals",label:"Appeals",icon:Scale},
    {href:"/review/communications",label:"Communications",icon:MailCheck},
  ]},
  {label:"Financial operations",items:[
    {href:"/review/financial",label:"Financial handoff",icon:BadgeDollarSign,roles:financeRoles},
    {href:"/review/accounting",label:"Accounting",icon:BookOpenCheck,roles:financeRoles},
    {href:"/review/financial-investigations",label:"Investigations",icon:ShieldAlert,roles:financeRoles},
    {href:"/review/recovery-operations",label:"Recovery",icon:RefreshCcw,roles:financeRoles},
    {href:"/review/provider-disputes",label:"Provider disputes",icon:FileSearch2,roles:financeRoles},
    {href:"/review/recovery-settlements",label:"Settlement closeout",icon:Banknote,roles:financeRoles},
    {href:"/review/financial-intelligence",label:"Financial intelligence",icon:Activity,roles:financeRoles},
    {href:"/review/recovery-settlement-intelligence",label:"Recovery intelligence",icon:Gauge,roles:financeRoles},
    {href:"/review/recovery-control-assurance",label:"Control Assurance",icon:ShieldCheck,roles:["finance_analyst","accounting_controller","auditor","tenant_admin"]},
  ]},
  {label:"Regulatory",items:[
    {href:"/review/regulatory-examination-readiness",label:"Examination readiness",icon:ClipboardCheck,roles:regulatoryRoles},
    {href:"/review/regulatory-examinations",label:"Examinations",icon:FileSearch2,roles:regulatoryRoles},
    {href:"/review/regulatory-examination-commitments",label:"Commitments",icon:BookOpenCheck,roles:regulatoryRoles},
    {href:"/review/regulatory-remediation",label:"Remediation",icon:RefreshCcw,roles:regulatoryRoles},
    {href:"/review/regulatory-transport",label:"Regulatory Transport",icon:MailCheck,roles:["auditor","tenant_admin"]},
    {href:"/review/regulatory-supervision",label:"Regulatory Supervision",icon:ShieldCheck,roles:regulatoryRoles},
    {href:"/review/regulatory-portfolio-oversight",label:"Portfolio assurance",icon:Gauge,roles:regulatoryRoles},
  ]},
  {label:"AI & platform",items:[{href:"/review/ai-ops",label:"AI operations",icon:Bot,roles:["tenant_admin","auditor"]}]},
];

function active(pathname:string,href:string){return href==="/review"?pathname===href:pathname===href||pathname.startsWith(`${href}/`)}

export function AppShell({ children }: { children: React.ReactNode }) {
  const [session,setSession]=useState<ReviewerSession|null>(null); const [mobileOpen,setMobileOpen]=useState(false); const pathname=usePathname();
  useEffect(()=>{reviewerApi.session().then(setSession).catch(()=>null)},[]);
  useEffect(()=>setMobileOpen(false),[pathname]);
  const groups=useMemo(()=>nav.map(g=>({...g,items:g.items.filter(i=>!i.roles||(session&&i.roles.includes(session.role)))})).filter(g=>g.items.length),[session]);
  const sidebar=<>
    <div className="h-16 px-4 border-b border-[#20364e] flex items-center justify-between">
      <Link href="/review" className="flex items-center gap-2.5"><span className="h-9 w-9 rounded-xl bg-teal-400/15 border border-teal-300/30 grid place-items-center"><ShieldCheck className="h-5 w-5 text-teal-300"/></span><span><span className="font-bold block leading-4">MedClaimIQ</span><span className="text-[10px] uppercase tracking-[.14em] text-slate-500">Review operations</span></span></Link>
      <button className="btn btn-ghost p-2 lg:hidden" aria-label="Close navigation" onClick={()=>setMobileOpen(false)}><X className="h-4 w-4"/></button>
    </div>
    <nav aria-label="Reviewer navigation" className="nav-scroll flex-1 overflow-y-auto px-3 py-4">
      {groups.map(group=><div key={group.label} className="mb-5"><div className="px-3 mb-1.5 text-[10px] font-bold uppercase tracking-[.14em] text-slate-600">{group.label}</div><div className="space-y-1">{group.items.map(item=>{const Icon=item.icon;const current=active(pathname,item.href);return <Link key={item.href} href={item.href} aria-current={current?"page":undefined} className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-semibold transition ${current?"bg-teal-400/12 text-teal-200 border border-teal-300/20":"text-slate-400 hover:bg-white/5 hover:text-slate-100 border border-transparent"}`}><Icon className="h-4 w-4 shrink-0"/><span>{item.label}</span></Link>})}</div></div>)}
    </nav>
    <div className="border-t border-[#20364e] p-3"><div className="flex items-center gap-3 rounded-xl bg-[#0b1726] p-3"><UserRound className="h-5 w-5 text-slate-500"/><div className="min-w-0 flex-1"><div className="truncate text-sm font-semibold capitalize">{session?.role?.replaceAll("_"," ")||"Reviewer"}</div><div className="truncate mono text-[10px] text-slate-500">{session?.tenant_id||"Loading identity…"}</div></div><form action="/api/auth/logout" method="post"><button className="btn btn-ghost p-2" aria-label="Sign out" title="Sign out"><LogOut className="h-4 w-4"/></button></form></div></div>
  </>;
  return <div className="min-h-screen">
    <a href="#review-main" className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-[100] focus:rounded-lg focus:bg-white focus:text-slate-950 focus:px-3 focus:py-2">Skip to main content</a>
    <aside className="hidden lg:flex fixed inset-y-0 left-0 z-50 w-72 flex-col border-r border-[#20364e] bg-[#07111ff5] backdrop-blur-xl">{sidebar}</aside>
    {mobileOpen&&<div className="lg:hidden fixed inset-0 z-[60] bg-black/60" onMouseDown={e=>{if(e.target===e.currentTarget)setMobileOpen(false)}}><aside className="h-full w-[min(88vw,320px)] flex flex-col border-r border-[#20364e] bg-[#07111f]">{sidebar}</aside></div>}
    <div className="lg:pl-72 min-h-screen">
      <header className="sticky top-0 z-40 h-16 border-b border-[#20364e] bg-[#07111fee] backdrop-blur-xl flex items-center justify-between px-4 md:px-7">
        <div className="flex items-center gap-3"><button className="btn btn-ghost p-2 lg:hidden" aria-label="Open navigation" aria-expanded={mobileOpen} onClick={()=>setMobileOpen(true)}><Menu className="h-5 w-5"/></button><div><div className="text-xs text-slate-500">Secure Claims Operations</div><div className="text-sm font-semibold flex items-center gap-2"><Activity className="h-3.5 w-3.5 text-emerald-300"/>Evidence-grounded · Human controlled</div></div></div>
        <div className="hidden sm:flex items-center gap-2 text-xs text-slate-400"><ShieldCheck className="h-4 w-4 text-teal-300"/>Least privilege session</div>
      </header>
      <main id="review-main" className="px-4 md:px-7 py-6 max-w-[1700px] mx-auto">{children}</main>
    </div>
  </div>;
}
