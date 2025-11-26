import { useState, useEffect } from "react";
import { kbApi, KBHealthResponse } from "../services/apiService";

export function useKBHealth() {
  const [healthStatus, setHealthStatus] = useState<KBHealthResponse | null>(
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
      const anyReady =
        data.knowledge_bases?.some((kb) => kb.index_ready) ?? false;
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
