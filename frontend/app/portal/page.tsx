import { ProviderRecoveryBalanceStatements } from "@/components/portal/provider-recovery-balance-statements";
import { RecoverySettlementCenter } from "@/components/portal/recovery-settlement-center";
import { ProviderDisputeCenter } from "@/components/portal/provider-dispute-center";
import { PortalClaimList } from "@/components/portal/claim-list";
import { backendRequest } from "@/lib/server/backend";

export default async function PortalPage(){
  const response=await backendRequest("/api/v1/auth/me");
  if(!response.ok) throw new Error("Unable to resolve portal role");
  const identity=await response.json() as {role?:unknown};
  const role=String(identity.role||"");
  const providerOperations=role==="provider"||role==="hospital_admin";
  return <>
    <PortalClaimList/>
    {providerOperations&&<><ProviderDisputeCenter/><RecoverySettlementCenter/><ProviderRecoveryBalanceStatements/></>}
  </>;
}
