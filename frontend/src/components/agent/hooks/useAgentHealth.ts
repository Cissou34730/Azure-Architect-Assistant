import { useState, useEffect } from "react";

const API_BASE = `${import.meta.env.BACKEND_URL || "http://localhost:8000"}/api`;

type AgentStatus = "unknown" | "healthy" | "not_initialized";

export function useAgentHealth() {
  const [agentStatus, setAgentStatus] = useState<AgentStatus>("unknown");

  const checkHealth = async () => {
    try {
      const response = await fetch(`${API_BASE}/agent/health`);
      const data = await response.json();
      setAgentStatus(data.status);
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
