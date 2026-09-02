"use client";
import { PageError } from "@/components/ui/page-state";
export default function ReviewError({error,reset}:{error:Error & {digest?:string};reset:()=>void}){return <PageError title="Review operations are temporarily unavailable" detail={error.digest?`Reference ${error.digest}. No decision or mutation was automatically retried.`:"No decision or mutation was automatically retried. Retry the workspace when ready."} retry={reset}/>}
