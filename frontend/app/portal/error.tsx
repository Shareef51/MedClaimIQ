"use client";
import { PortalError } from "@/components/ui/page-state";
export default function PortalRouteError({error,reset}:{error:Error & {digest?:string};reset:()=>void}){return <PortalError title="Your claim portal is temporarily unavailable" detail={error.digest?`Reference ${error.digest}. No submission was automatically repeated.`:"No submission was automatically repeated. Please retry."} retry={reset}/>}
