// OLD TAB SYSTEM - Disabled in favor of UnifiedProjectPage
// Keeping imports and registrations commented out for reference
// If you need to revert to the old 3-tab structure, uncomment these lines

import { registerTab } from "./registry";
import { overviewTab } from "./definitions/overview";
import { workspaceTab } from "./definitions/workspace";
import { deliverablesTab } from "./definitions/deliverables";

// Register new tabs (3-tab structure) - DISABLED
// registerTab(overviewTab);
// registerTab(workspaceTab);
// registerTab(deliverablesTab);

export { getTabs } from "./registry";
export * from "./types";
