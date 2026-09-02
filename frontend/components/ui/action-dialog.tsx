"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import { X } from "lucide-react";

export type DialogField = {
  name: string; label: string; type?: "text" | "textarea" | "select" | "date"; placeholder?: string; defaultValue?: string;
  required?: boolean; options?: Array<{ value: string; label: string }>; help?: string;
};

type Props = {
  open: boolean; title: string; description?: string; fields: DialogField[]; submitLabel?: string; danger?: boolean;
  busy?: boolean; onClose: () => void; onSubmit: (values: Record<string, string>) => Promise<void> | void;
};

export function ActionDialog({ open, title, description, fields, submitLabel="Confirm", danger=false, busy=false, onClose, onSubmit }: Props) {
  const initial = useMemo(() => Object.fromEntries(fields.map((f) => [f.name, f.defaultValue ?? ""])), [fields]);
  const [values, setValues] = useState<Record<string,string>>(initial);
  const panelRef = useRef<HTMLDivElement>(null);
  useEffect(() => { if (open) setValues(initial); }, [open, initial]);
  useEffect(() => {
    if (!open) return;
    const previouslyFocused=document.activeElement instanceof HTMLElement?document.activeElement:null;
    const panel = panelRef.current;
    const focusables = () => Array.from(panel?.querySelectorAll<HTMLElement>('button:not([disabled]),input:not([disabled]),textarea:not([disabled]),select:not([disabled])') ?? []);
    focusables()[0]?.focus();
    const key = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !busy) onClose();
      if (event.key !== "Tab") return;
      const list = focusables(); if (!list.length) return;
      const first=list[0], last=list[list.length-1];
      if (event.shiftKey && document.activeElement===first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement===last) { event.preventDefault(); first.focus(); }
    };
    document.addEventListener("keydown", key); return () => { document.removeEventListener("keydown", key); previouslyFocused?.focus(); };
  }, [open, busy, onClose]);
  if (!open) return null;
  return <div className="dialog-backdrop" onMouseDown={(e)=>{if(e.target===e.currentTarget&&!busy)onClose()}}>
    <div ref={panelRef} role="dialog" aria-modal="true" aria-labelledby="action-dialog-title" aria-describedby={description?"action-dialog-description":undefined} className="dialog-panel">
      <div className="flex items-start justify-between gap-4 border-b border-[#233b55] p-5">
        <div><h2 id="action-dialog-title" className="text-lg font-bold">{title}</h2>{description&&<p id="action-dialog-description" className="mt-1 text-sm text-slate-400">{description}</p>}</div>
        <button className="btn btn-ghost p-2" aria-label="Close dialog" onClick={onClose} disabled={busy}><X className="h-4 w-4"/></button>
      </div>
      <form className="space-y-4 p-5" onSubmit={(e)=>{e.preventDefault();void onSubmit(values)}}>
        {fields.map((field)=><label key={field.name} className="block"><span className="text-sm font-semibold">{field.label}</span>
          {field.help&&<span className="block text-xs text-slate-500 mt-1">{field.help}</span>}
          {field.type==="textarea"?<textarea className="input mt-2 min-h-28" required={field.required} placeholder={field.placeholder} value={values[field.name]??""} onChange={e=>setValues(v=>({...v,[field.name]:e.target.value}))}/>
          :field.type==="select"?<select className="input mt-2" required={field.required} value={values[field.name]??""} onChange={e=>setValues(v=>({...v,[field.name]:e.target.value}))}>{field.options?.map(o=><option key={o.value} value={o.value}>{o.label}</option>)}</select>
          :<input type={field.type==="date"?"date":"text"} className="input mt-2" required={field.required} placeholder={field.placeholder} value={values[field.name]??""} onChange={e=>setValues(v=>({...v,[field.name]:e.target.value}))}/>}</label>)}
        <div className="flex justify-end gap-2 pt-2"><button type="button" className="btn btn-ghost" onClick={onClose} disabled={busy}>Cancel</button><button className={`btn ${danger?"btn-danger":"btn-primary"}`} disabled={busy}>{busy?"Working…":submitLabel}</button></div>
      </form>
    </div>
  </div>;
}

export function InfoDialog({open,title,body,onClose}:{open:boolean;title:string;body:string;onClose:()=>void}){
  const panelRef=useRef<HTMLDivElement>(null);
  useEffect(()=>{
    if(!open)return;
    const previouslyFocused=document.activeElement instanceof HTMLElement?document.activeElement:null;
    const panel=panelRef.current;
    const focusables=()=>Array.from(panel?.querySelectorAll<HTMLElement>('button:not([disabled]),a[href],input:not([disabled]),textarea:not([disabled]),select:not([disabled])')??[]);
    focusables()[0]?.focus();
    const key=(event:KeyboardEvent)=>{
      if(event.key==="Escape")onClose();
      if(event.key!=="Tab")return;
      const list=focusables();if(!list.length)return;const first=list[0],last=list[list.length-1];
      if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus()}else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus()}
    };
    document.addEventListener("keydown",key);
    return()=>{document.removeEventListener("keydown",key);previouslyFocused?.focus()};
  },[open,onClose]);
  if(!open)return null;
  return <div className="dialog-backdrop" onMouseDown={e=>{if(e.target===e.currentTarget)onClose()}}><div ref={panelRef} role="dialog" aria-modal="true" aria-labelledby="info-dialog-title" aria-describedby="info-dialog-body" className="dialog-panel max-w-lg"><div className="p-5"><div className="flex justify-between gap-4"><h2 id="info-dialog-title" className="text-lg font-bold">{title}</h2><button className="btn btn-ghost p-2" aria-label="Close dialog" onClick={onClose}><X className="h-4 w-4"/></button></div><p id="info-dialog-body" className="mt-4 rounded-xl border border-[#233b55] bg-[#07111f] p-3 text-sm break-all mono">{body}</p><div className="mt-5 flex justify-end"><button className="btn btn-primary" onClick={onClose}>Done</button></div></div></div></div>
}
