"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, RefreshCw, Send, ShieldCheck } from "lucide-react";
import { reviewerApi } from "@/lib/api";
import type { RegulatoryTransportDashboard } from "@/lib/regulatory-schemas";

function Metric({ label, value }: { label: string; value: string }) {
  return <div className="panel p-4"><div className="text-xs uppercase tracking-[.12em] text-slate-500">{label.replaceAll("_", " ")}</div><div className="mt-2 text-2xl font-bold">{value}</div></div>;
}

export default function RegulatoryTransportPage() {
  const [data, setData] = useState<RegulatoryTransportDashboard | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  async function refresh() {
    try { setError(""); setData(await reviewerApi.regulatoryTransportDashboard()); }
    catch (e) { setError(e instanceof Error ? e.message : "Unable to load regulatory transport operations"); }
    finally { setLoading(false); }
  }

  useEffect(() => {
    void refresh();
    const es = new EventSource("/api/reviewer/events");
    es.onmessage = (event) => { if (event.data.includes("regulatory_transport.")) void refresh(); };
    return () => es.close();
  }, []);

  return <div className="space-y-5">
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div><div className="text-xs uppercase tracking-[.18em] text-teal-300">Regulatory operations</div><h1 className="text-2xl md:text-3xl font-bold">Regulatory Submission Transport</h1><p className="mt-1 text-sm text-slate-400">Human-certified report → one-time human release → encrypted signed transport → verified regulator acknowledgment.</p></div>
      <button type="button" className="btn btn-ghost" onClick={() => void refresh()} aria-label="Refresh regulatory transport"><RefreshCw className="h-4 w-4"/>Refresh</button>
    </div>

    <section className="panel p-4" aria-labelledby="transport-authority"><div className="flex items-center gap-2 font-semibold" id="transport-authority"><ShieldCheck className="h-4 w-4 text-teal-300"/>Authority boundary</div><p className="mt-2 text-sm text-slate-400">AI, agent workflows, retrieval and workers cannot certify reports or authorize regulatory release. Workers execute only previously human-released transmissions and cannot alter financial records, authorize payments, collect funds or move money.</p></section>

    {loading && <div className="panel p-5 text-sm text-slate-400" role="status">Loading regulatory transmission status…</div>}
    {error && <div className="panel p-4 border-rose-400/30 text-rose-300" role="alert">{error}</div>}

    {data && <>
      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5" aria-label="Regulatory transport metrics">{Object.entries(data.kpis).map(([key, value]) => <Metric key={key} label={key} value={String(value ?? "—")}/>)}</section>
      <section className="panel p-5"><div className="flex items-center gap-2 font-semibold"><Send className="h-4 w-4 text-teal-300"/>Transmission operations</div>
        <div className="mt-4 space-y-3">{data.transmissions.map((item) => <article key={item.transmission_id} className="rounded-xl border border-[#20364e] p-4 text-sm"><div className="flex flex-wrap items-center justify-between gap-2"><strong className="mono text-xs">{item.transmission_id}</strong><span className="badge">{item.status.replaceAll("_", " ")}</span></div><dl className="mt-3 grid gap-2 text-xs sm:grid-cols-2 lg:grid-cols-4"><div><dt className="text-slate-500">Attempts</dt><dd>{item.attempt_count}</dd></div><div><dt className="text-slate-500">External reference</dt><dd className="break-all">{item.external_submission_reference || "Pending"}</dd></div><div><dt className="text-slate-500">Destination</dt><dd className="break-all">{item.destination_id}</dd></div><div><dt className="text-slate-500">Envelope</dt><dd className="mono truncate" title={item.envelope_sha256}>{item.envelope_sha256.slice(0, 16)}…</dd></div></dl></article>)}
          {data.transmissions.length === 0 && <div className="rounded-xl border border-dashed border-[#29445f] p-8 text-center text-sm text-slate-400">No regulatory transmissions are currently recorded for this organization.</div>}
        </div>
      </section>
      {data.incidents.length > 0 && <section className="panel p-5" aria-labelledby="transport-incidents"><div className="flex items-center gap-2 font-semibold" id="transport-incidents"><AlertTriangle className="h-4 w-4 text-amber-300"/>Open transport incidents</div><div className="mt-3 space-y-2">{data.incidents.map((incident) => <div key={incident.incident_id} className="rounded-lg border border-amber-400/20 p-3 text-sm"><strong>{incident.type.replaceAll("_", " ")}</strong><span className="ml-2 badge">{incident.status}</span></div>)}</div></section>}
    </>}
  </div>;
}
