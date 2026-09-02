"use client";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertTriangle, Clock3, ListFilter, RefreshCw, Radio, Search, ShieldAlert } from "lucide-react";
import { reviewerApi } from "@/lib/api";
import { useEventStream } from "@/lib/hooks/use-event-stream";
import type { ReviewQueueItem } from "@/lib/schemas";

function bandClass(band: string) { return `badge badge-${["critical","high","normal","low"].includes(band) ? band : "normal"}`; }
function dueText(value: string | null) {
  if (!value) return "—";
  const ms = new Date(value).getTime() - Date.now();
  if (ms <= 0) return `Overdue ${Math.max(1, Math.round(Math.abs(ms)/60000))}m`;
  if (ms < 3600000) return `${Math.max(1, Math.round(ms/60000))}m`;
  return `${Math.round(ms/3600000)}h`;
}

export function ReviewQueue() {
  const [items, setItems] = useState<ReviewQueueItem[]>([]);
  const [mine, setMine] = useState(false);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try { setError(null); setItems(await reviewerApi.queue(mine)); }
    catch (e) { setError(e instanceof Error ? e.message : "Queue unavailable"); }
    finally { setLoading(false); }
  }, [mine]);
  useEffect(() => { setLoading(true); void load(); }, [load]);
  const { state } = useEventStream("/api/reviewer/queue/events", () => { void load(); });

  const filtered = useMemo(() => items.filter((item) => !query || `${item.claim_id} ${item.priority_band} ${item.status} ${item.priority_reasons.join(" ")}`.toLowerCase().includes(query.toLowerCase())), [items, query]);
  const critical = items.filter((i) => i.priority_band === "critical").length;
  const high = items.filter((i) => i.priority_band === "high").length;
  const overdue = items.filter((i) => i.sla_due_at && new Date(i.sla_due_at).getTime() < Date.now()).length;

  return <div className="space-y-6">
    <div className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-5">
      <div><div className="panel-title">Claims operations</div><h1 className="text-3xl font-bold tracking-tight mt-1">Human review queue</h1><p className="text-slate-400 mt-2 max-w-2xl">Deterministic priority from SLA risk, guardrail escalations, human checkpoints, material contradictions, and claim state.</p></div>
      <div className="flex items-center gap-2"><span className="badge"><Radio className={`h-3.5 w-3.5 ${state === "open" ? "text-emerald-300" : "text-amber-300"}`} />{state === "open" ? "Live" : "Reconnecting"}</span><button className="btn" onClick={() => void load()}><RefreshCw className="h-4 w-4" />Refresh</button><button className="btn btn-primary" onClick={async () => { setLoading(true); try { setItems(await reviewerApi.refreshQueue()); } finally { setLoading(false); } }}><ListFilter className="h-4 w-4" />Recalculate priority</button></div>
    </div>

    <div className="grid sm:grid-cols-2 xl:grid-cols-4 gap-4">
      <div className="card p-5"><div className="panel-title">Open work</div><div className="metric mt-2">{items.length}</div><div className="muted text-xs mt-1">Reviewable claims</div></div>
      <div className="card p-5"><div className="panel-title">Critical</div><div className="metric mt-2 text-rose-300">{critical}</div><div className="muted text-xs mt-1">Immediate human attention</div></div>
      <div className="card p-5"><div className="panel-title">High priority</div><div className="metric mt-2 text-amber-200">{high}</div><div className="muted text-xs mt-1">Elevated evidence/SLA risk</div></div>
      <div className="card p-5"><div className="panel-title">Overdue SLA</div><div className="metric mt-2 text-orange-200">{overdue}</div><div className="muted text-xs mt-1">Timers past due</div></div>
    </div>

    <section className="card overflow-hidden">
      <div className="p-4 border-b border-[#233b55] flex flex-col md:flex-row md:items-center justify-between gap-3">
        <div className="relative flex-1 max-w-lg"><label htmlFor="review-queue-search" className="sr-only">Search the review queue</label><Search className="absolute left-3 top-3 h-4 w-4 text-slate-500" aria-hidden="true"/><input id="review-queue-search" className="input pl-9" placeholder="Search claim, priority, reason…" value={query} onChange={(e) => setQuery(e.target.value)} /></div>
        <label className="flex items-center gap-2 text-sm text-slate-300"><input type="checkbox" checked={mine} onChange={(e) => setMine(e.target.checked)} /> Assigned to me</label>
      </div>
      {error && <div role="alert" className="p-4 bg-rose-950/20 text-rose-200 border-b border-rose-500/20"><AlertTriangle className="inline h-4 w-4 mr-2" />{error}</div>}
      <div className="table-wrap">
        <table><caption className="sr-only">Claims requiring human review, prioritized by evidence and SLA risk</caption><thead><tr><th>Priority</th><th>Claim</th><th>Status</th><th>Why now</th><th>Reviewer</th><th>SLA</th><th></th></tr></thead><tbody>
          {loading && !items.length && <tr><td colSpan={7} className="text-slate-400">Loading review queue…</td></tr>}
          {!loading && !filtered.length && <tr><td colSpan={7} className="text-slate-400">No claims match this view.</td></tr>}
          {filtered.map((item) => <tr key={item.work_item_id}>
            <td><span className={bandClass(item.priority_band)}>{item.priority_band} · {item.priority_score}</span></td>
            <td><div className="font-semibold mono">{item.claim_id}</div><div className="text-xs text-slate-500 mt-1">Work item {item.work_item_id.slice(-8)}</div></td>
            <td><span className="badge">{item.status.replaceAll("_", " ")}</span></td>
            <td><div className="flex flex-wrap gap-1.5 max-w-sm">{item.priority_reasons.slice(0,4).map((r) => <span key={r} className="text-xs px-2 py-1 rounded-md bg-[#162a40] text-slate-300">{r.replaceAll("_", " ")}</span>)}</div></td>
            <td className="text-slate-300">{item.assigned_reviewer_user_id ? <span className="mono text-xs">{item.assigned_reviewer_user_id}</span> : <span className="text-slate-500">Unassigned</span>}</td>
            <td>{item.sla_due_at ? <span className={`flex items-center gap-1.5 text-sm ${new Date(item.sla_due_at).getTime() < Date.now() ? "text-rose-300" : "text-slate-300"}`}><Clock3 className="h-4 w-4" />{dueText(item.sla_due_at)}</span> : "—"}</td>
            <td><Link className="btn btn-primary" href={`/review/claims/${encodeURIComponent(item.claim_id)}`}>{item.priority_band === "critical" ? <ShieldAlert className="h-4 w-4" /> : null}Open</Link></td>
          </tr>)}
        </tbody></table>
      </div>
    </section>
  </div>;
}
