import { ClaimWorkbench } from "@/components/review/claim-workbench";
export default async function ClaimPage({ params }: { params: Promise<{ claimId: string }> }) {
  const { claimId } = await params;
  return <ClaimWorkbench claimId={claimId} />;
}
