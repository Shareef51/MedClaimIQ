"use client";
import { useEffect, useState } from "react";
import { Activity, AlertTriangle, Clock3, MailCheck, RefreshCw, ShieldCheck, Workflow } from "lucide-react";
import { reviewerApi } from "@/lib/api";

type Dashboard=Awaited<ReturnType<typeof reviewerApi.communicationDashboard>>;

export default function CommunicationOperationsPage(){
  const [data,setData]=useState<Dashboard|null>(null); const [error,setError]=useState<string|null>(null);
  const load=async()=>{try{setError(null);setData(await reviewerApi.communicationDashboard())}catch(e){setError(e instanceof Error?e.message:"Communication operations unavailable")}};
  useEffect(()=>{void load()},[]);
  return <div className="space-y-5">
    <section className="card p-6 border-teal-400/20"><div className="flex items-start justify-between gap-4"><div><div className="panel-title">communication control plane</div><h1 className="text-2xl font-bold mt-1">Delivery, compliance & reconciliation</h1><p className="mt-2 max-w-4xl text-sm text-slate-400">Email, SMS and portal delivery operate only on human-released notice artifacts. Transport workers, webhooks, providers and retry automation have no claim adjudication authority.</p></div><ShieldCheck className="h-9 w-9 text-teal-300"/></div></section>
    {error&&<div className="rounded-xl border border-rose-500/30 bg-rose-950/30 p-3 text-sm text-rose-200"><AlertTriangle className="inline h-4 w-4 mr-2"/>{error}</div>}
    {!data?<section className="card p-5 text-sm text-slate-400">Loading delivery operations…</section>:<>
      <section className="grid sm:grid-cols-2 xl:grid-cols-5 gap-3"><Kpi label="Delivery SLO" value={`${data.delivery_slo_percent}%`} icon={<Activity/>}/><Kpi label="Queued / retry" value={String(data.queued)} icon={<Workflow/>}/><Kpi label="Delivered" value={String(data.delivered)} icon={<MailCheck/>}/><Kpi label="Deadline breaches" value={String(data.deadline_breaches)} icon={<Clock3/>}/><Kpi label="Open incidents" value={String(data.open_incidents)} icon={<AlertTriangle/>}/></section>
      <div className="grid lg:grid-cols-2 gap-5"><section className="card p-5"><div className="panel-title">Transport state</div><div className="grid grid-cols-2 gap-3 mt-4"><Mini label="Total dispatches" value={data.total_dispatches}/><Mini label="Waiting receipt" value={data.sent_waiting_receipt}/><Mini label="Bounced" value={data.bounced}/><Mini label="Dead-lettered" value={data.dead_lettered}/></div></section><section className="card p-5"><div className="panel-title">Governance</div><ul className="mt-4 space-y-2 text-sm text-slate-300"><li>• Destinations encrypted at rest and never exposed in reviewer payloads.</li><li>• Approved template versions use independent human approval.</li><li>• Provider webhooks are signature-verified and idempotent.</li><li>• Legal holds block disposition; automated destructive purge is disabled.</li><li>• Current transport adjudication authority: <b className="text-teal-300">{data.adjudication_authority}</b>.</li></ul></section></div>
      <button className="btn btn-ghost" onClick={()=>void load()}><RefreshCw className="h-4 w-4"/>Refresh metrics</button>
    </>}
  </div>
}
function Kpi({label,value,icon}:{label:string;value:string;icon:React.ReactNode}){return <div className="card p-4"><div className="flex items-center justify-between text-slate-500"><span className="text-xs uppercase tracking-wider">{label}</span><span className="h-4 w-4">{icon}</span></div><div className="text-2xl font-bold mt-2">{value}</div></div>}
function Mini({label,value}:{label:string;value:number|string}){return <div className="rounded-xl bg-[#091727] border border-[#1f3852] p-3"><div className="text-[11px] uppercase tracking-wider text-slate-500">{label}</div><div className="font-bold mt-1">{value}</div></div>}
