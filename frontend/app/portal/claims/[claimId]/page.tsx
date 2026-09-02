import { ClaimDetail } from "@/components/portal/claim-detail";
export default async function PortalClaimPage({params}:{params:Promise<{claimId:string}>}){const {claimId}=await params;return <ClaimDetail claimId={claimId}/>}
