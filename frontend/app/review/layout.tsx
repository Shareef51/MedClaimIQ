import { redirect } from "next/navigation";
import { hasReviewerSession } from "@/lib/server/session";
import { backendRequest } from "@/lib/server/backend";
import { AppShell } from "@/components/review/app-shell";
export default async function ReviewLayout({children}:{children:React.ReactNode}){
 if(!(await hasReviewerSession()))redirect("/login");
 let destination:string|null=null;
 try{const r=await backendRequest("/api/v1/auth/me"); if(!r.ok)destination="/login"; else {const s=await r.json();if(["patient","provider","hospital_admin"].includes(String(s.role)))destination="/portal";}}catch{destination="/login"}
 if(destination)redirect(destination);
 return <AppShell>{children}</AppShell>
}
