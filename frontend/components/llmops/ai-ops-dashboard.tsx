"use client";
import { useEffect, useState } from "react";
import { Activity, AlertTriangle, Bot, Coins, Gauge, RefreshCw, Search, Wrench } from "lucide-react";
import { reviewerApi } from "@/lib/api";
import type { LLMOpsSummary } from "@/lib/schemas";

function Metric({label,value,sub}:{label:string;value:string;sub?:string}){
  return <div className="panel p-4"><div className="text-xs uppercase tracking-[.12em] text-slate-500">{label}</div><div className="mt-2 text-2xl font-bold text-slate-100">{value}</div>{sub&&<div className="mt-1 text-xs text-slate-500">{sub}</div>}</div>;
}

export function AIOpsDashboard(){
  const [data,setData]=useState<LLMOpsSummary|null>(null); const [error,setError]=useState<string|null>(null); const [windowMinutes,setWindowMinutes]=useState(60);
  async function load(){try{setError(null);setData(await reviewerApi.llmopsSummary(windowMinutes));}catch(e){setError(e instanceof Error?e.message:"Unable to load AI operations");}}
  useEffect(()=>{void load();const id=setInterval(()=>void load(),30000);return()=>clearInterval(id);},[windowMinutes]);
  return <div className="space-y-5">
    <div className="flex flex-wrap items-center justify-between gap-3"><div><div className="text-xs uppercase tracking-[.18em] text-teal-300">AI operations</div><h1 className="text-2xl md:text-3xl font-bold">LLMOps observability</h1><p className="text-sm text-slate-400 mt-1">PHI-safe operational telemetry across retrieval, agents, models, tools, evaluations and SLOs.</p></div><div className="flex gap-2"><select className="input" value={windowMinutes} onChange={e=>setWindowMinutes(Number(e.target.value))}><option value={60}>Last hour</option><option value={360}>Last 6 hours</option><option value={1440}>Last 24 hours</option></select><button className="btn btn-ghost" onClick={()=>void load()}><RefreshCw className="h-4 w-4"/>Refresh</button></div></div>
    {error&&<div role="alert" className="panel p-4 border-rose-400/30 text-rose-300">{error}</div>}
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
      <Metric label="Model calls" value={String(data?.model_calls??"—")} sub={`${data?.input_tokens??0} input / ${data?.output_tokens??0} output tokens`}/>
      <Metric label="Estimated cost" value={data?.estimated_cost_usd==null?"Unpriced":`$${data.estimated_cost_usd.toFixed(4)}`} sub={`${data?.unpriced_model_calls??0} calls without configured price`}/>
      <Metric label="Retrieval P95" value={`${Math.round(data?.retrieval_latency_p95_ms??0)} ms`} sub={`${data?.retrieval_runs??0} retrieval runs`}/>
      <Metric label="Agent error rate" value={`${((data?.agent_error_rate??0)*100).toFixed(1)}%`} sub={`${data?.agent_executions??0} agent executions`}/>
      <Metric label="MCP error rate" value={`${((data?.mcp_error_rate??0)*100).toFixed(1)}%`} sub={`${data?.mcp_invocations??0} tool invocations`}/>
    </div>
    <div className="grid gap-4 lg:grid-cols-2">
      <section className="panel p-5"><div className="flex items-center gap-2 font-semibold"><Bot className="h-4 w-4 text-teal-300"/>Model and quality operations</div><div className="mt-4 grid grid-cols-2 gap-3 text-sm"><div><span className="text-slate-500">Models</span><div className="mt-2 space-y-1">{Object.entries(data?.model_counts??{}).map(([m,c])=><div key={m} className="flex justify-between gap-3"><span className="mono text-xs">{m}</span><span>{c}</span></div>)}{Object.keys(data?.model_counts??{}).length===0&&<span className="text-slate-500">No model calls in window</span>}</div></div><div className="space-y-3"><div><span className="text-slate-500">No-evidence rate</span><div className="font-semibold">{((data?.retrieval_no_evidence_rate??0)*100).toFixed(1)}%</div></div><div><span className="text-slate-500">Evaluation block rate</span><div className="font-semibold">{((data?.evaluation_block_rate??0)*100).toFixed(1)}%</div></div></div></div></section>
      <section className="panel p-5"><div className="flex items-center gap-2 font-semibold"><AlertTriangle className="h-4 w-4 text-amber-300"/>SLO events</div><div className="mt-4 space-y-2">{(data?.slo_events??[]).map((e)=><div key={e.slo_event_id} className="rounded-xl border border-[#20364e] p-3 flex items-center justify-between gap-4"><div><div className="font-medium">{String(e.slo_kind).replaceAll("_"," ")}</div><div className="text-xs text-slate-500">Observed {e.observed_value} / threshold {e.threshold_value}</div></div><span className={e.severity==="critical"?"badge text-rose-300":"badge text-amber-300"}>{e.severity}</span></div>)}{(data?.slo_events??[]).length===0&&<div className="text-sm text-emerald-300">No recorded SLO breach events in the current tenant.</div>}</div></section>
    </div>
    <div className="panel p-4 text-xs text-slate-500 flex flex-wrap gap-x-6 gap-y-2"><span className="flex items-center gap-1"><Gauge className="h-3.5 w-3.5"/>Trace IDs correlate FastAPI → RAG → LangGraph → MCP → Kafka.</span><span className="flex items-center gap-1"><Search className="h-3.5 w-3.5"/>Raw reviewer queries and retrieved evidence are excluded from telemetry.</span><span className="flex items-center gap-1"><Coins className="h-3.5 w-3.5"/>Cost remains unpriced until provider pricing is explicitly configured.</span></div>
  </div>;
}
