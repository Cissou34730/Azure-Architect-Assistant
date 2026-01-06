import { lazy } from "react";
import { useProjectContext } from "../../context/ProjectContext";

const ProposalPanel = lazy(() => import("../../components/ProposalPanel").then(m => ({ default: m.ProposalPanel })));

export function ProposalTabAdapter() {
  const {
    architectureProposal,
    proposalStage,
    handleGenerateProposal,
    loading,
  } = useProjectContext();

  return (
    <ProposalPanel
      architectureProposal={architectureProposal}
      proposalStage={proposalStage}
      onGenerateProposal={handleGenerateProposal}
      loading={loading}
    />
  );
}
