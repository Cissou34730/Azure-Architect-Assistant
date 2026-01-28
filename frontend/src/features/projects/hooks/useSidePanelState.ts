import { useState, useEffect, useCallback } from "react";

export function useSidePanelState() {
  const [leftPanelOpen, setLeftPanelOpen] = useState(() => {
    const stored = localStorage.getItem("leftPanelOpen");
    return stored !== null ? stored === "true" : true;
  });

  const [rightPanelOpen, setRightPanelOpen] = useState(() => {
    const stored = localStorage.getItem("rightPanelOpen");
    return stored !== null ? stored === "true" : true;
  });

  useEffect(() => {
    localStorage.setItem("leftPanelOpen", String(leftPanelOpen));
  }, [leftPanelOpen]);

  useEffect(() => {
    localStorage.setItem("rightPanelOpen", String(rightPanelOpen));
  }, [rightPanelOpen]);

  const toggleLeftPanel = useCallback(() => {
    setLeftPanelOpen((prev) => !prev);
  }, []);

  const toggleRightPanel = useCallback(() => {
    setRightPanelOpen((prev) => !prev);
  }, []);

  return {
    leftPanelOpen,
    rightPanelOpen,
    toggleLeftPanel,
    toggleRightPanel,
  };
}
