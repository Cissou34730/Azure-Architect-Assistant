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
