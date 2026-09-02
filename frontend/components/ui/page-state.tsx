"use client";

import { AlertTriangle, LoaderCircle, RefreshCw } from "lucide-react";

export function PageLoading({ title = "Loading workspace…", detail = "Retrieving tenant-scoped data and permissions." }: { title?: string; detail?: string }) {
  return <div role="status" aria-live="polite" className="card p-6 flex items-start gap-3">
    <LoaderCircle className="h-5 w-5 shrink-0 animate-spin text-teal-300" aria-hidden="true"/>
    <div><div className="font-semibold">{title}</div><div className="text-sm text-slate-400 mt-1">{detail}</div></div>
  </div>;
}

export function PageError({ title = "This workspace could not be loaded", detail, retry }: { title?: string; detail: string; retry?: () => void }) {
  return <div role="alert" className="card p-6 border-rose-400/30">
    <div className="flex items-start gap-3"><AlertTriangle className="h-5 w-5 shrink-0 text-rose-300" aria-hidden="true"/><div className="min-w-0"><div className="font-semibold text-rose-100">{title}</div><div className="text-sm text-slate-400 mt-1 break-words">{detail}</div>{retry&&<button type="button" className="btn mt-4" onClick={retry}><RefreshCw className="h-4 w-4"/>Try again</button>}</div></div>
  </div>;
}

export function PortalLoading({ title = "Loading claim information…" }: { title?: string }) {
  return <div role="status" aria-live="polite" className="rounded-xl border border-slate-200 bg-white p-5 text-slate-700 flex items-center gap-3"><LoaderCircle className="h-5 w-5 animate-spin text-teal-700" aria-hidden="true"/><span className="font-semibold">{title}</span></div>;
}

export function PortalError({ title = "We could not load this information", detail, retry }: { title?: string; detail: string; retry?: () => void }) {
  return <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-5 text-rose-900"><div className="flex items-start gap-3"><AlertTriangle className="h-5 w-5 shrink-0" aria-hidden="true"/><div><div className="font-semibold">{title}</div><div className="text-sm mt-1 text-rose-800">{detail}</div>{retry&&<button type="button" className="mt-4 rounded-lg border border-rose-300 bg-white px-3 py-2 text-sm font-semibold" onClick={retry}><RefreshCw className="inline h-4 w-4 mr-2"/>Try again</button>}</div></div></div>;
}
