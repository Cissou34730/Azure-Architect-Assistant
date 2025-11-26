import { useState, useEffect } from "react";

interface KB {
  id: string;
  name: string;
  status: string;
  profiles: string[];
  priority: number;
}

interface KBListResponse {
  knowledge_bases: KB[];
}

export function useKBList() {
  const [availableKBs, setAvailableKBs] = useState<KB[]>([]);
  const [selectedKBs, setSelectedKBs] = useState<string[]>([]);
  const [isLoadingKBs, setIsLoadingKBs] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void fetchKBList();
  }, []);

  const fetchKBList = async () => {
    try {
      setIsLoadingKBs(true);
      setError(null);

      const response = await fetch("http://localhost:8000/api/kb/list");
      if (!response.ok) {
        throw new Error(`Failed to fetch KB list: ${response.statusText}`);
      }

      const data: KBListResponse = await response.json();
      setAvailableKBs(data.knowledge_bases);

      // Auto-select all active KBs with kb-query profile
      const autoSelect = data.knowledge_bases
        .filter((kb) => kb.status === "active" && kb.profiles.includes("kb-query"))
        .map((kb) => kb.id);
      setSelectedKBs(autoSelect);

      console.log(`[KB List] Loaded ${data.knowledge_bases.length} KBs, auto-selected ${autoSelect.length}`);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unknown error";
      setError(message);
      console.error("[KB List] Failed to fetch:", err);
    } finally {
      setIsLoadingKBs(false);
    }
  };

  return {
    availableKBs,
    selectedKBs,
    setSelectedKBs,
    isLoadingKBs,
    error,
    refreshKBList: fetchKBList,
  };
}
