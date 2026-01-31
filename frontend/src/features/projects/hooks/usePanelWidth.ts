import { useCallback, useEffect, useMemo, useState } from "react";

interface UsePanelWidthOptions {
  readonly storageKey: string;
  readonly defaultWidth: number;
  readonly minWidth: number;
  readonly maxWidth: number;
}

function clampWidth(value: number, minWidth: number, maxWidth: number): number {
  return Math.max(minWidth, Math.min(maxWidth, value));
}

export function usePanelWidth({
  storageKey,
  defaultWidth,
  minWidth,
  maxWidth,
}: UsePanelWidthOptions) {
  const initialWidth = useMemo(() => {
    const stored = localStorage.getItem(storageKey);
    const parsed = stored !== null ? Number(stored) : Number.NaN;
    if (!Number.isFinite(parsed)) {
      return defaultWidth;
    }
    return clampWidth(parsed, minWidth, maxWidth);
  }, [storageKey, defaultWidth, minWidth, maxWidth]);

  const [width, setWidth] = useState(initialWidth);

  useEffect(() => {
    localStorage.setItem(storageKey, String(width));
  }, [storageKey, width]);

  const setClampedWidth = useCallback(
    (next: number) => {
      setWidth(clampWidth(next, minWidth, maxWidth));
    },
    [minWidth, maxWidth],
  );

  return {
    width,
    setWidth: setClampedWidth,
  };
}
