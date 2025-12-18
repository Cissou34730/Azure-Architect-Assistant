import { useState, useEffect } from "react";
import type { AgentStatus } from "../../../types/agent";

const API_BASE = `${import.meta.env.BACKEND_URL || "http://localhost:8000"}/api`;

export function useAgentHealth() {
  const [agentStatus, setAgentStatus] = useState<AgentStatus>("unknown");

  const checkHealth = async () => {
    try {
      const response = await fetch(`${API_BASE}/agent/health`);
      const data = await response.json();
      // Validate and map the status to ensure it's a valid AgentStatus
      const status = data.status as AgentStatus;
      if (status === "healthy" || status === "not_initialized" || status === "unknown") {
        setAgentStatus(status);
      } else {
        console.warn(`Unknown agent status received: ${data.status}`);
        setAgentStatus("unknown");
      }
    } catch (error) {
      console.error("Failed to check agent health:", error);
      setAgentStatus("not_initialized");
    }
  };

  useEffect(() => {
    void checkHealth();
  }, []);

  return { agentStatus, refreshHealth: checkHealth };
}
