"use client";
import Link from "next/link";
import { useCallback,useEffect,useState } from "react";
import { CalendarClock, FileUp, RefreshCw } from "lucide-react";
import { portalApi } from "@/lib/api";
import type { PortalClaimListItem } from "@/lib/schemas";
import { PortalError, PortalLoading } from "@/components/ui/page-state";

export function PortalClaimList(){
 const [items,setItems]=useState<PortalClaimListItem[]>([]); const [loading,setLoading]=useState(true); const [error,setError]=useState("");
 const load=useCallback(async()=>{setLoading(true);setError("");try{setItems(await portalApi.claims())}catch(e){setItems([]);setError(e instanceof Error?e.message:"Claims are temporarily unavailable")}finally{setLoading(false)}},[]);
 useEffect(()=>{void load()},[load]);
 return <section aria-labelledby="portal-claims-heading"><div className="mb-6"><p className="text-sm font-semibold text-teal-700">Your claims</p><h1 id="portal-claims-heading" className="text-3xl font-bold tracking-tight">Claim status and document requests</h1><p className="mt-2 text-slate-600">See current status, respond to requests, and track documents you submitted.</p></div>
 <div className="space-y-3" aria-live="polite">{loading&&<PortalLoading title="Loading your claims…"/>}{!loading&&error&&<PortalError title="Claims could not be loaded" detail={error} retry={()=>void load()}/>} {!loading&&!error&&items.length===0&&<div className="rounded-xl border bg-white p-6 text-slate-600">No claims are available for this relationship.</div>}{!error&&items.map(c=><Link key={c.claim_id} href={`/portal/claims/${encodeURIComponent(c.claim_id)}`} className="block rounded-2xl border bg-white p-5 shadow-sm hover:border-teal-300 focus-visible:outline-teal-600"><div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4"><div><div className="text-xs uppercase tracking-wide text-slate-500">{c.external_claim_ref}</div><div className="mt-1 text-lg font-bold">{c.status.replaceAll("_"," ")}</div><div className="mt-2 text-sm text-slate-600">Service date {c.service_from} · {c.currency} {c.total_amount}</div></div><div className="flex flex-wrap gap-3"><span className="rounded-full bg-amber-50 px-3 py-1.5 text-xs font-semibold text-amber-800"><FileUp className="inline h-3.5 w-3.5 mr-1"/>{c.outstanding_request_count} requests</span>{c.next_deadline_at&&<span className="rounded-full bg-sky-50 px-3 py-1.5 text-xs font-semibold text-sky-800"><CalendarClock className="inline h-3.5 w-3.5 mr-1"/>Deadline {new Date(c.next_deadline_at).toLocaleDateString()}</span>}</div></div></Link>)}</div>
 {!loading&&!error&&<button type="button" onClick={()=>void load()} className="mt-5 rounded-lg border bg-white px-3 py-2 text-sm font-semibold"><RefreshCw className="inline h-4 w-4 mr-2"/>Refresh</button>}</section>
}
