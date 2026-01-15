import { useState, useEffect } from "react";
import { kbApi } from "../services/kbService";
import { KbHealthResponse } from "../types/api";

export function useKBHealth() {
  const [healthStatus, setHealthStatus] = useState<KbHealthResponse | null>(
    null
  );
  const [isReady, setIsReady] = useState(false);
  const [isChecking, setIsChecking] = useState(true);

  const checkHealth = async () => {
    try {
      setIsChecking(true);
      const data = await kbApi.checkHealth();
      setHealthStatus(data);

      // Check if at least one KB is ready
      const anyReady = data.knowledgeBases.some((kb) => kb.indexReady);
      setIsReady(anyReady);
    } catch (error) {
      console.error("Error checking KB health:", error);
      setIsReady(false);
      setHealthStatus(null);
    } finally {
      setIsChecking(false);
    }
  };

  useEffect(() => {
    void checkHealth();
  }, []);

  return {
    healthStatus,
    isReady,
    isChecking,
    refreshHealth: checkHealth,
  };
}
