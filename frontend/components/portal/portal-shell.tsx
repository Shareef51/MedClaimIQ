"use client";
import Link from "next/link";
import { useEffect,useState } from "react";
import { FileHeart, LogOut, UserRound } from "lucide-react";
import { reviewerApi } from "@/lib/api";
import type { ReviewerSession } from "@/lib/schemas";
export function PortalShell({children}:{children:React.ReactNode}){
 const [session,setSession]=useState<ReviewerSession|null>(null); useEffect(()=>{reviewerApi.session().then(setSession).catch(()=>null)},[]);
 return <div className="portal-theme min-h-screen bg-slate-50 text-slate-950"><a href="#portal-main" className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:rounded-lg focus:bg-white focus:px-3 focus:py-2">Skip to claim content</a>
  <header className="sticky top-0 z-40 border-b bg-white/95 backdrop-blur"><div className="mx-auto max-w-6xl h-16 px-4 flex items-center justify-between">
   <Link href="/portal" className="flex items-center gap-3"><span className="h-10 w-10 rounded-xl bg-teal-50 border border-teal-200 grid place-items-center"><FileHeart className="h-5 w-5 text-teal-700"/></span><span><b>MedClaimIQ</b><span className="block text-xs text-slate-500">Claim status & documents</span></span></Link>
   <div className="flex items-center gap-3"><span className="hidden sm:flex items-center gap-2 text-sm text-slate-600"><UserRound className="h-4 w-4"/>{session?.role?.replaceAll("_"," ")||"Portal user"}</span><form action="/api/auth/logout" method="post"><button className="rounded-lg border px-3 py-2 text-sm font-semibold"><LogOut className="inline h-4 w-4 mr-2"/>Sign out</button></form></div>
  </div></header><main id="portal-main" className="mx-auto max-w-6xl p-4 md:p-6">{children}</main>
 </div>
}
