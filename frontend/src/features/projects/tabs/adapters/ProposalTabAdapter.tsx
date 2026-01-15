import { lazy } from "react";
import { useProjectContext } from "../../context/useProjectContext";

const PROPOSAL_PANEL_LAZY = lazy(() =>
  import("../../components/ProposalPanel").then((m) => ({
    default: m.ProposalPanel,
  })),
);

export function ProposalTabAdapter() {
  const {
    architectureProposal,
    proposalStage,
    handleGenerateProposal,
    loading,
  } = useProjectContext();

  const PROPOSAL_PANEL = PROPOSAL_PANEL_LAZY;

  return (
    <PROPOSAL_PANEL
      architectureProposal={architectureProposal}
      proposalStage={proposalStage}
      onGenerateProposal={handleGenerateProposal}
      loading={loading}
    />
  );
}
