"use client";
import { useState } from "react";

export function Kpi({label,value,detail}:{label:string;value:string|number;detail?:string}){
  return <div className="card kpi p-4 animate-in">
    <div className="text-[10px] uppercase tracking-wider text-slate-500">{label}</div>
    <div className="text-xl font-bold mt-2 break-all">{String(value)}</div>
    {detail&&<div className="text-xs text-slate-500 mt-1">{detail}</div>}
  </div>;
}

export function Panel({title,children}:{title:string;children:React.ReactNode}){
  return <section className="card p-5 animate-in">
    <div className="panel-title">{title}</div>
    <div className="mt-3 space-y-2">{children}</div>
  </section>;
}

export function Row({title,right,sub,hash}:{title:string;right?:string;sub:string;hash?:string}){
  const [selected,setSelected]=useState(false);
  return <div
    className={`row${selected?" row-selected":""}`}
    role="button" tabIndex={0} aria-pressed={selected}
    onClick={()=>setSelected(s=>!s)}
    onKeyDown={e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();setSelected(s=>!s)}}}
  >
    <div className="flex justify-between gap-3 text-sm"><b>{title}</b>{right&&<span>{right}</span>}</div>
    <div className="text-xs text-slate-500 mt-1 break-all">{sub}</div>
    {hash&&<div className="mono text-[10px] text-slate-600 mt-1 break-all">{hash}</div>}
  </div>;
}

export function Empty({text="No records available."}:{text?:string}){
  return <p className="text-sm text-slate-500">{text}</p>;
}
