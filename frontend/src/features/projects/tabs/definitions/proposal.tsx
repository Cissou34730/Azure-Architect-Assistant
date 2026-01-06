import { ProjectTab } from "../types";
import { ProposalTabAdapter } from "../adapters/ProposalTabAdapter";

export const proposalTab: ProjectTab = {
  id: "proposal",
  label: "Proposal",
  path: "proposal",
  component: ProposalTabAdapter,
};
