"use client";
import { PageError } from "@/components/ui/page-state";
export default function GlobalError({error,reset}:{error:Error & {digest?:string};reset:()=>void}){return <main className="min-h-screen p-6 md:p-10"><div className="mx-auto max-w-3xl"><PageError title="MedClaimIQ encountered an unexpected error" detail={error.digest?`Reference ${error.digest}. Your action was not automatically retried.`:"Your action was not automatically retried. Please retry or return to sign in if the problem continues."} retry={reset}/></div></main>}
