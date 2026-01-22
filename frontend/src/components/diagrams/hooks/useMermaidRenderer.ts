import { useEffect, useRef, useState, useCallback } from "react";
import mermaid from "mermaid";

interface UseMermaidRendererProps {
  sourceCode: string;
  diagramId: string;
}

export function useMermaidRenderer({
  sourceCode,
  diagramId,
}: UseMermaidRendererProps) {
  const [renderError, setRenderError] = useState<string | null>(null);
  const [isRendered, setIsRendered] = useState(false);
  const mermaidRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    mermaid.initialize({
      startOnLoad: false,
      theme: "default",
      securityLevel: "antiscript",
      fontFamily: "ui-sans-serif, system-ui, sans-serif",
    });
  }, []);

  const renderCurrentDiagram = useCallback(async () => {
    const container = mermaidRef.current;
    if (container === null) {
      return;
    }

    try {
      setRenderError(null);
      setIsRendered(false);

      // Clean up previous content
      container.innerHTML = "";

      // Render the diagram
      const { svg } = await mermaid.render(`mermaid-${diagramId}`, sourceCode);

      container.innerHTML = svg;
      setIsRendered(true);
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Mermaid rendering failed";
      setRenderError(errorMessage);
      console.error("Mermaid Render Error:", err);
    }
  }, [sourceCode, diagramId]);

  useEffect(() => {
    void renderCurrentDiagram();
  }, [renderCurrentDiagram]);

  return {
    mermaidRef,
    renderError,
    isRendered,
  };
}
