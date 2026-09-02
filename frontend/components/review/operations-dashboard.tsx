"use client";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Activity, AlertTriangle, Bot, Clock3, FileSearch2, Gauge, RefreshCw, ShieldAlert, TrendingUp } from "lucide-react";
import { reviewerApi } from "@/lib/api";
import type { ReviewQueueItem, LLMOpsSummary, ReviewerSession, RecoveryOperationsPortfolio } from "@/lib/schemas";
import type { RegulatoryExaminationDashboard } from "@/lib/regulatory-schemas";

type Slice={label:string;value:number;display?:string};
function Bars({items,max}:{items:Slice[];max?:number}){const ceiling=Math.max(max??0,...items.map(x=>x.value),1);return <div className="space-y-3">{items.map(x=><div key={x.label}><div className="mb-1 flex justify-between gap-3 text-xs"><span className="text-slate-400">{x.label}</span><b>{x.display??x.value}</b></div><div className="chart-track" role="img" aria-label={`${x.label}: ${x.display??x.value}`}><div className="chart-fill" style={{width:`${Math.min(100,Math.max(2,(x.value/ceiling)*100))}%`}}/></div></div>)}</div>}
function Kpi({label,value,detail}:{label:string;value:string;detail:string}){return <div className="card p-4"><div className="panel-title">{label}</div><div className="metric mt-2">{value}</div><div className="text-xs text-slate-500 mt-1">{detail}</div></div>}
function Panel({title,icon,children,href}:{title:string;icon:React.ReactNode;children:React.ReactNode;href?:string}){return <section className="card p-5"><div className="flex items-center justify-between gap-3"><div className="flex items-center gap-2 font-bold">{icon}{title}</div>{href&&<Link className="text-xs text-teal-300 hover:text-teal-200" href={href}>Open workbench →</Link>}</div><div className="mt-4">{children}</div></section>}

export function OperationsDashboard(){
 const [session,setSession]=useState<ReviewerSession|null>(null),[queue,setQueue]=useState<ReviewQueueItem[]>([]),[llm,setLlm]=useState<LLMOpsSummary|null>(null),[recovery,setRecovery]=useState<RecoveryOperationsPortfolio|null>(null),[reg,setReg]=useState<RegulatoryExaminationDashboard|null>(null),[loading,setLoading]=useState(true),[updated,setUpdated]=useState<Date|null>(null),[warnings,setWarnings]=useState<string[]>([]);
 const load=useCallback(async()=>{setLoading(true);const nextWarnings:string[]=[];let current=session;try{current=current??await reviewerApi.session();setSession(current)}catch{nextWarnings.push("Session details unavailable")}
   const results=await Promise.allSettled([reviewerApi.queue(false),reviewerApi.llmopsSummary(60),reviewerApi.recoveryOperationsPortfolio(),reviewerApi.regulatoryExaminationDashboard()]);
   if(results[0].status==="fulfilled")setQueue(results[0].value);else nextWarnings.push("Claims metrics unavailable");
   if(results[1].status==="fulfilled")setLlm(results[1].value);else setLlm(null);
   if(results[2].status==="fulfilled")setRecovery(results[2].value);else setRecovery(null);
   if(results[3].status==="fulfilled")setReg(results[3].value);else setReg(null);
   setWarnings(nextWarnings);setUpdated(new Date());setLoading(false);
 },[session]);
 useEffect(()=>{void load()},[load]);
 const risk=useMemo(()=>["critical","high","normal","low"].map(label=>({label:`${label[0].toUpperCase()}${label.slice(1)} risk`,value:queue.filter(q=>q.priority_band===label).length})),[queue]);
 const now=Date.now(); const sla=useMemo(()=>[
   {label:"Overdue",value:queue.filter(q=>q.sla_due_at&&new Date(q.sla_due_at).getTime()<now).length},
   {label:"Due < 1 hour",value:queue.filter(q=>{if(!q.sla_due_at)return false;const d=new Date(q.sla_due_at).getTime()-now;return d>=0&&d<3600000}).length},
   {label:"Due 1–4 hours",value:queue.filter(q=>{if(!q.sla_due_at)return false;const d=new Date(q.sla_due_at).getTime()-now;return d>=3600000&&d<14400000}).length},
   {label:"Due > 4 hours",value:queue.filter(q=>!q.sla_due_at||new Date(q.sla_due_at).getTime()-now>=14400000).length},
 ],[queue,now]);
 const openMaterial=reg?.cases.reduce((n,c)=>n+c.open_material_findings,0)??0; const openCommitments=reg?.cases.reduce((n,c)=>n+c.open_commitments,0)??0;
 return <div className="space-y-6">
  <div className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-4"><div><div className="panel-title">Operations command center</div><h1 className="text-3xl font-bold tracking-tight mt-1">Claims, recovery, regulatory & AI health</h1><p className="text-sm text-slate-400 mt-2 max-w-3xl">Live operational signals for human reviewers. Metrics are tenant-scoped and advisory; business and regulatory decisions remain human-controlled.</p></div><button className="btn" onClick={()=>void load()} disabled={loading}><RefreshCw className={`h-4 w-4 ${loading?"animate-spin":""}`}/>Refresh dashboard</button></div>
  {warnings.length>0&&<div role="status" className="card p-3 text-sm text-amber-200"><AlertTriangle className="inline h-4 w-4 mr-2"/>{warnings.join(" · ")}. Restricted modules remain hidden when your role does not have access.</div>}
  <div className="grid sm:grid-cols-2 xl:grid-cols-5 gap-3"><Kpi label="Open claims" value={String(queue.length)} detail="Human review queue"/><Kpi label="SLA overdue" value={String(sla[0].value)} detail="Immediate workflow attention"/><Kpi label="Recovery rate" value={recovery?`${recovery.recovery_rate_percent.toFixed(1)}%`:"Restricted"} detail={recovery?`${recovery.open_cases} open recovery cases`:"Role-based access"}/><Kpi label="Regulatory exposure" value={reg?String(openMaterial):"Restricted"} detail={reg?`${openCommitments} open commitments`:"Role-based access"}/><Kpi label="Agent P95" value={llm?`${Math.round(llm.agent_latency_p95_ms)} ms`:"Restricted"} detail={llm?`${llm.agent_executions} executions / 60m`:"AI Ops role required"}/></div>
  <div className="grid xl:grid-cols-2 gap-5">
   <Panel title="Claim volume & risk" icon={<ShieldAlert className="h-4 w-4 text-rose-300"/>} href="/review/claims"><Bars items={risk}/></Panel>
   <Panel title="SLA aging" icon={<Clock3 className="h-4 w-4 text-amber-300"/>} href="/review/claims"><Bars items={sla}/></Panel>
   <Panel title="Recovery trend & progress" icon={<TrendingUp className="h-4 w-4 text-emerald-300"/>} href="/review/recovery-operations">{recovery?<><Bars max={100} items={[{label:"Verified recovery",value:recovery.recovery_rate_percent,display:`${recovery.recovery_rate_percent.toFixed(1)}%`},{label:"Remaining exposure",value:Math.max(0,100-recovery.recovery_rate_percent),display:`${Math.max(0,100-recovery.recovery_rate_percent).toFixed(1)}%`} ]}/><div className="grid grid-cols-2 gap-3 mt-4 text-xs text-slate-400"><span>Identified: <b className="text-slate-200">{recovery.identified_leakage}</b></span><span>Verified: <b className="text-slate-200">{recovery.verified_recovered}</b></span></div></>:<Restricted text="Recovery analytics requires a finance, audit, or administrator role."/>}</Panel>
   <Panel title="Regulatory exposure" icon={<FileSearch2 className="h-4 w-4 text-sky-300"/>} href="/review/regulatory-examination-readiness">{reg?<Bars items={[{label:"Open examination cases",value:Number(reg.kpis.open_cases??0)},{label:"Overdue responses",value:Number(reg.kpis.overdue??0)},{label:"Material findings",value:openMaterial},{label:"Open commitments",value:openCommitments}]}/>:<Restricted text="Regulatory exposure metrics require an audit, compliance, or administrator role."/>}</Panel>
   <Panel title="RAG quality" icon={<Gauge className="h-4 w-4 text-teal-300"/>} href="/review/ai-ops">{llm?<Bars max={100} items={[{label:"Evidence-backed retrieval",value:(1-llm.retrieval_no_evidence_rate)*100,display:`${((1-llm.retrieval_no_evidence_rate)*100).toFixed(1)}%`},{label:"Evaluation pass rate",value:(1-llm.evaluation_block_rate)*100,display:`${((1-llm.evaluation_block_rate)*100).toFixed(1)}%`} ]}/>:<Restricted text="RAG quality telemetry requires AI Operations access."/>}</Panel>
   <Panel title="Agent & retrieval latency" icon={<Bot className="h-4 w-4 text-violet-300"/>} href="/review/ai-ops">{llm?<Bars items={[{label:"Agent P95",value:llm.agent_latency_p95_ms,display:`${Math.round(llm.agent_latency_p95_ms)} ms`},{label:"Retrieval P95",value:llm.retrieval_latency_p95_ms,display:`${Math.round(llm.retrieval_latency_p95_ms)} ms`},{label:"Model P95",value:llm.model_latency_p95_ms,display:`${Math.round(llm.model_latency_p95_ms)} ms`} ]}/>:<Restricted text="Latency telemetry requires AI Operations access."/>}</Panel>
  </div>
  <div className="text-xs text-slate-500 flex flex-wrap gap-4"><span className="flex items-center gap-1"><Activity className="h-3.5 w-3.5"/>Session role: {session?.role?.replaceAll("_"," ")??"loading"}</span><span>Last refreshed: {updated?updated.toLocaleTimeString():"—"}</span></div>
 </div>
}
function Restricted({text}:{text:string}){return <div className="rounded-xl border border-dashed border-[#31506f] p-5 text-sm text-slate-500">{text}</div>}
