"use client";
import { useEffect,useState } from "react";
import { AlertTriangle } from "lucide-react";
import { portalApi } from "@/lib/api";
import type { BalanceStatement } from "@/lib/portal-operations-schemas";
export function ProviderRecoveryBalanceStatements(){
 const [items,setItems]=useState<BalanceStatement[]|null>(null),[error,setError]=useState("");
 useEffect(()=>{portalApi.recoveryBalanceStatements().then(x=>{setItems(x);setError("")}).catch(e=>{setItems([]);setError(e instanceof Error?e.message:"Balance statements unavailable")})},[]);
 return <section className="mt-6 card p-5"><h2 className="text-xl font-semibold">Recovery balance statements</h2><p className="text-sm text-slate-500 mt-1">Human-released, immutable read-only statements. These statements do not initiate collection or change a recovery balance.</p>{error&&<div role="alert" className="mt-4 rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700"><AlertTriangle className="inline h-4 w-4 mr-2"/>{error}</div>}{items===null?<State text="Loading recovery balance statements…"/>:items.length===0?<State text="No released recovery balance statements are available."/>:<div className="mt-4 space-y-3">{items.map(x=><article key={x.statement_id} className="rounded-xl border border-slate-200 p-4"><div className="flex justify-between gap-3"><b>Statement version {x.statement_version}</b><span className="text-sm">{String(x.as_of_date)}</span></div><div className="grid sm:grid-cols-3 gap-3 mt-3 text-sm"><div>Target <b>{x.target_recovery} {x.currency}</b></div><div>Verified <b>{x.verified_recovery}</b></div><div>Remaining <b>{x.remaining_balance}</b></div></div><div className="mt-2 text-xs text-slate-500 break-all">SHA-256 {x.payload_sha256}</div></article>)}</div>}</section>
}
function State({text}:{text:string}){return <div className="mt-4 rounded-xl border border-dashed border-slate-300 bg-slate-50 p-4 text-sm text-slate-500">{text}</div>}
