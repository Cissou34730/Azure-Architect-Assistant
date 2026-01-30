import { useEffect, useState, useCallback, useMemo } from "react";
import { getMermaid } from "../../../utils/mermaidConfig";
import { useIntersectionObserver } from "../../../hooks/useIntersectionObserver";
import { diagramCache } from "../../../utils/diagramCache";

interface UseMermaidRendererProps {
  sourceCode: string;
  entityId: string; // The unique ID of the diagram entity
  domId: string; // The unique ID for this specific DOM instance
}

// Helper to generate a simple hash of the source code
function getHashCode(str: string): string {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = (hash << 5) - hash + char;
    hash = hash & hash; // Convert to 32bit integer
  }
  return Math.abs(hash).toString(36);
}

// eslint-disable-next-line max-lines-per-function -- Hook stays cohesive; extra lines are for clarity and error handling.
export function useMermaidRenderer({
  sourceCode,
  entityId,
  domId,
}: UseMermaidRendererProps) {
  const [renderError, setRenderError] = useState<string | null>(null);
  const [isRendered, setIsRendered] = useState(false);
  const cacheKey = useMemo(
    () => `cache-${entityId}-${getHashCode(sourceCode)}`,
    [entityId, sourceCode],
  );
  const { ref, isVisible, hasBeenVisible } =
    useIntersectionObserver<HTMLDivElement>({
      rootMargin: "200px", // Start rendering slightly before it enters viewport
      threshold: 0.1,
      freezeOnceVisible: true,
    });
  const mermaidRef = ref;
  const renderCurrentDiagram = useCallback(async () => {
    const container = mermaidRef.current;
    if (container === null || !hasBeenVisible) return;

    const cachedSvg = diagramCache.get(cacheKey);
    if (cachedSvg !== null) {
      container.innerHTML = cachedSvg;
      setIsRendered(true);
      return;
    }

    try {
      setRenderError(null);
      container.innerHTML = "";
      const { svg } = await (
        await getMermaid()
      ).render(`mermaid-${domId}`, sourceCode);
      diagramCache.set(cacheKey, svg);
      container.innerHTML = svg;
      setIsRendered(true);
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Mermaid rendering failed";
      setRenderError(errorMessage);
      console.error("Mermaid Render Error:", err);
    }
  }, [sourceCode, domId, cacheKey, hasBeenVisible]);

  useEffect(() => {
    if (hasBeenVisible) {
      void renderCurrentDiagram();
    }
  }, [hasBeenVisible, renderCurrentDiagram]);

  return {
    mermaidRef,
    renderError,
    isRendered,
    isVisible,
  };
}
