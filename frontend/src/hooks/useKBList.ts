import { useState, useEffect } from "react";

interface KB {
  id: string;
  name: string;
  status: string;
  profiles: string[];
  priority: number;
  index_ready?: boolean;
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

      const baseUrl = import.meta.env.BACKEND_URL;
      const response = await fetch(`${baseUrl}/api/kb/list`);
      if (!response.ok) {
        throw new Error(`Failed to fetch KB list: ${response.statusText}`);
      }

      const data: KBListResponse = await response.json();
      // Fetch health to augment list with index readiness
      let healthIndexMap: Record<string, boolean> = {};
      try {
        const healthRes = await fetch(`${baseUrl}/api/kb/health`);
        if (healthRes.ok) {
          const healthData = await healthRes.json();
          const kbArray = (healthData?.knowledge_bases || []) as Array<{
            kb_id: string;
            index_ready: boolean;
          }>;
          healthIndexMap = kbArray.reduce<Record<string, boolean>>(
            (acc, kb) => {
              acc[kb.kb_id] = kb.index_ready === true;
              return acc;
            },
            {}
          );
        } else {
          console.warn(`[KB List] Health fetch failed: ${healthRes.status}`);
        }
      } catch (e) {
        console.warn("[KB List] Health fetch error:", e);
      }

      // Merge index_ready from health into list
      const mergedKBs = data.knowledge_bases.map((kb) => ({
        ...kb,
        index_ready: healthIndexMap[kb.id] ?? kb.index_ready,
      }));

      setAvailableKBs(mergedKBs);

      // Auto-select all active and indexed KBs with kb-query profile
      const autoSelect = mergedKBs
        .filter(
          (kb) =>
            kb.status === "active" &&
            kb.profiles.includes("kb-query") &&
            kb.index_ready !== false
        )
        .map((kb) => kb.id);
      setSelectedKBs(autoSelect);
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
