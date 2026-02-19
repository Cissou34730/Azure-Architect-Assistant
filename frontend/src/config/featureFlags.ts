/**
 * Feature Flags Configuration
 *
 * Controlled by environment variables prefix with VITE_
 */
export const featureFlags = Object.freeze({
  // Use incremental chat updates (only append new messages)
  enableIncrementalChat:
    import.meta.env.VITE_ENABLE_INCREMENTAL_CHAT === "true",

  // Use optimistic UI for chat messages
  enableOptimisticChat: import.meta.env.VITE_ENABLE_OPTIMISTIC_CHAT === "true",

  // Enable debug render counters
  enableRenderCounters: import.meta.env.VITE_ENABLE_RENDER_COUNTERS === "true",

  // Cap in-memory chat messages (uses messageArchive utility)
  enableChatArchiving: import.meta.env.VITE_ENABLE_CHAT_ARCHIVING !== "false", // Enabled by default

  // Unified upload + analysis frontend workflow state
  enableUnifiedInputWorkflow:
    import.meta.env.VITE_ENABLE_UNIFIED_INPUT_WORKFLOW !== "false",

  // Inline initialization flow (Inputs -> Upload -> Analyze -> Complete)
  enableUnifiedProjectInitialization:
    import.meta.env.VITE_ENABLE_UNIFIED_PROJECT_INITIALIZATION !== "false",

  // Per-document parse/analyze status in left panel traces
  enableDocumentStatusTrace:
    import.meta.env.VITE_ENABLE_DOCUMENT_STATUS_TRACE !== "false",
});

/**
 * Check if a specific feature is enabled
 *
 * @param flag - The flag name
 * @returns boolean
 */
export function isFeatureEnabled(flag: keyof typeof featureFlags): boolean {
  return featureFlags[flag];
}
