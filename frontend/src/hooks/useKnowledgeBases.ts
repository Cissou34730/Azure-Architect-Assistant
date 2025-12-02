/**
 * React hook for managing knowledge bases
 */

import { useState, useEffect, useCallback } from "react";
import { KnowledgeBase } from "../types/ingestion";
import { listKBs } from "../services/ingestionApi";

interface UseKnowledgeBasesReturn {
  kbs: KnowledgeBase[];
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

/**
 * Hook to fetch and manage list of knowledge bases
 */
export function useKnowledgeBases(): UseKnowledgeBasesReturn {
  const [kbs, setKbs] = useState<KnowledgeBase[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchKBs = useCallback(async () => {
    try {
      setLoading(true);
      const data = await listKBs();
      setKbs([...data]);
      setError(null);
    } catch (err) {
      const error =
        err instanceof Error
          ? err
          : new Error("Failed to fetch knowledge bases");
      setError(error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchKBs();
  }, [fetchKBs]);

  return {
    kbs,
    loading,
    error,
    refetch: fetchKBs,
  };
}
