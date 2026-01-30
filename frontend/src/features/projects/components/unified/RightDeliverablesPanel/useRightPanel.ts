import { useState, useCallback, useMemo } from "react";
import { useProjectStateContext } from "../../../context/useProjectStateContext";

export function useRightPanel() {
  const [expandedSections, setExpandedSections] = useState<ReadonlySet<string>>(
    new Set(["diagrams", "adrs", "findings"]),
  );
  const [searchQuery, setSearchQuery] = useState("");
  const { projectState } = useProjectStateContext();

  const toggleSection = useCallback((id: string) => {
    setExpandedSections((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

  const adrs = useMemo(() => projectState?.adrs ?? [], [projectState?.adrs]);
  const findings = useMemo(
    () => projectState?.findings ?? [],
    [projectState?.findings],
  );
  const costs = useMemo(
    () => projectState?.costEstimates ?? [],
    [projectState?.costEstimates],
  );
  const diagrams = useMemo(
    () => projectState?.diagrams ?? [],
    [projectState?.diagrams],
  );
  const reqCount = useMemo(
    () => projectState?.requirements.length ?? 0,
    [projectState?.requirements],
  );

  return {
    expandedSections,
    searchQuery,
    setSearchQuery,
    toggleSection,
    adrs,
    findings,
    costs,
    diagrams,
    reqCount,
  };
}
