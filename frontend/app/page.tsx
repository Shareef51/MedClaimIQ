import { redirect } from "next/navigation";
import { backendRequest } from "@/lib/server/backend";
export default async function Home(){
 let destination="/login";
 try{const r=await backendRequest("/api/v1/auth/me"); if(r.ok){const s=await r.json();const role=String(s.role||"");destination=["patient","provider","hospital_admin"].includes(role)?"/portal":"/review";}}catch{}
 redirect(destination);
}
