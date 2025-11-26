import { useState, useEffect } from "react";
import { useKBHealth } from "./useKBHealth";
import { useKBQuery } from "./useKBQuery";
import { useKBList } from "./useKBList";

export function useKBWorkspace() {
  const healthHook = useKBHealth();
  const queryHook = useKBQuery();
  const kbListHook = useKBList();

  // Optionally log actions here like in useProjectWorkspace
  useEffect(() => {
    if (healthHook.healthStatus) {
      const readyCount =
        healthHook.healthStatus.knowledge_bases?.filter((kb) => kb.index_ready)
          .length ?? 0;
      console.log(`[KB Workspace] ${readyCount} knowledge bases ready`);
    }
  }, [healthHook.healthStatus]);

  // Handler for submitting query with selected KBs
  const handleSubmitQuery = (e?: React.FormEvent) => {
    queryHook.submitQuery(e, kbListHook.selectedKBs);
  };

  return {
    // Health status
    healthStatus: healthHook.healthStatus,
    isReady: healthHook.isReady,
    isChecking: healthHook.isChecking,
    refreshHealth: healthHook.refreshHealth,

    // Query state
    question: queryHook.question,
    setQuestion: queryHook.setQuestion,
    response: queryHook.response,
    isLoading: queryHook.isLoading,
    submitQuery: handleSubmitQuery,
    askFollowUp: queryHook.askFollowUp,

    // KB selection
    availableKBs: kbListHook.availableKBs,
    selectedKBs: kbListHook.selectedKBs,
    setSelectedKBs: kbListHook.setSelectedKBs,
    isLoadingKBs: kbListHook.isLoadingKBs,
  };
}
