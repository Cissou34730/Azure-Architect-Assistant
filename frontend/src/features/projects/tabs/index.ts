import { registerTab } from "./registry";
import { documentsTab } from "./definitions/documents";
import { chatTab } from "./definitions/chat";
import { stateTab } from "./definitions/state";
import { proposalTab } from "./definitions/proposal";
import { diagramsTab } from "./definitions/diagrams";

// Register default tabs
registerTab(documentsTab);
registerTab(chatTab);
registerTab(stateTab);
registerTab(proposalTab);
registerTab(diagramsTab);

export { getTabs } from "./registry";
export * from "./types";
