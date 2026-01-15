import { useState, useEffect, useCallback } from "react";
import { kbApi } from "../services/kbService";
import { KbInfo } from "../types/api";

function getAutoSelectedKBs(kbs: readonly KbInfo[]): string[] {
  return kbs
    .filter(
      (kb) =>
        kb.status === "active" &&
        kb.profiles.includes("kb-query") &&
        kb.indexReady
    )
    .map((kb) => kb.id);
}

export function useKBList() {
  const [availableKBs, setAvailableKBs] = useState<readonly KbInfo[]>([]);
  const [selectedKBs, setSelectedKBs] = useState<readonly string[]>([]);
  const [isLoadingKBs, setIsLoadingKBs] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchKBList = useCallback(async () => {
    try {
      setIsLoadingKBs(true);
      setError(null);

      const [listData, healthData] = await Promise.all([
        kbApi.listKbs(),
        kbApi.checkHealth().catch(() => null),
      ]);

      const healthIndexMap: Record<string, boolean> = {};
      healthData?.knowledgeBases.forEach((kb) => {
        healthIndexMap[kb.kbId] = kb.indexReady;
      });

      const mergedKBs = listData.knowledgeBases.map((kb) => ({
        ...kb,
        indexReady: healthIndexMap[kb.id] ?? kb.indexReady,
      }));

      setAvailableKBs(mergedKBs);
      setSelectedKBs(getAutoSelectedKBs(mergedKBs));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setIsLoadingKBs(false);
    }
  }, []);

  useEffect(() => {
    void fetchKBList();
  }, [fetchKBList]);

  return {
    availableKBs,
    selectedKBs,
    setSelectedKBs,
    isLoadingKBs,
    error,
    refreshKBList: fetchKBList,
  };
}
