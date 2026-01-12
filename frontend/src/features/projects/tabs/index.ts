import { registerTab } from "./registry";
import { documentsTab } from "./definitions/documents";
import { chatTab } from "./definitions/chat";
import { stateTab } from "./definitions/state";
import { proposalTab } from "./definitions/proposal";
import { diagramsTab } from "./definitions/diagrams";
import { aaaTab } from "./definitions/aaa";

// Register default tabs
registerTab(documentsTab);
registerTab(chatTab);
registerTab(stateTab);
registerTab(proposalTab);
registerTab(diagramsTab);
registerTab(aaaTab);

export { getTabs } from "./registry";
export * from "./types";
