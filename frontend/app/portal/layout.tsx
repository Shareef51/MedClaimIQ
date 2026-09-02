import { redirect } from "next/navigation";
import { backendRequest } from "@/lib/server/backend";
import { hasReviewerSession } from "@/lib/server/session";
import { PortalShell } from "@/components/portal/portal-shell";
export default async function PortalLayout({children}:{children:React.ReactNode}){
 if(!(await hasReviewerSession()))redirect("/login");
 let destination:string|null=null;
 try{const r=await backendRequest("/api/v1/auth/me"); if(!r.ok)destination="/login"; else {const s=await r.json(); if(!["patient","provider","hospital_admin"].includes(String(s.role)))destination="/review";}}catch{destination="/login"}
 if(destination)redirect(destination);
 return <PortalShell>{children}</PortalShell>
}
