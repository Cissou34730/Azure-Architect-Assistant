import { ProjectTab } from "../types";
import { useProjectContext } from "../../context/ProjectContext";
import { ProposalPanel } from "../../components/ProposalPanel";

const ProposalComponent = () => {
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
};

export const proposalTab: ProjectTab = {
  id: "proposal",
  label: "Proposal",
  path: "proposal",
  component: ProposalComponent,
};
