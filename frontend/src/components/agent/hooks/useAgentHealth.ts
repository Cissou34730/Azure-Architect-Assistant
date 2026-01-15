import { useState, useEffect, useCallback } from "react";
import type { AgentStatus } from "../../../types/agent";
import { agentApi } from "../../../services/agentService";

export function useAgentHealth() {
  const [agentStatus, setAgentStatus] = useState<AgentStatus>("unknown");

  const checkHealth = useCallback(async () => {
    try {
      const data = await agentApi.getHealth();
      const rawStatus = data.status;

      if (
        rawStatus === "healthy" ||
        rawStatus === "not_initialized" ||
        rawStatus === "unknown"
      ) {
        setAgentStatus(rawStatus);
      } else {
        setAgentStatus("unknown");
      }
    } catch (error) {
      console.error("Failed to check agent health:", error);
      setAgentStatus("not_initialized");
    }
  }, []);

  useEffect(() => {
    void checkHealth();
  }, [checkHealth]);

  return { agentStatus, refreshHealth: checkHealth };
}
