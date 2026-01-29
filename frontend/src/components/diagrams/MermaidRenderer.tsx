import { useMemo } from "react";
import { Network } from "lucide-react";
import { useMermaidRenderer } from "./hooks/useMermaidRenderer";

interface MermaidRendererProps {
  readonly diagramId: string; // Entity ID (e.g. diag-123)
  readonly sourceCode: string;
  readonly diagramType?: string;
  readonly prefix?: string; // Optional prefix for DOM uniqueness
}

/**
 * MermaidRenderer Component
 *
 * Renders a single Mermaid diagram from source code.
 */
export default function MermaidRenderer({
  diagramId,
  sourceCode,
  diagramType = "diagram",
  prefix = "render",
}: MermaidRendererProps) {
  // Use a unique DOM ID but keep the entity ID for caching
  const domId = useMemo(() => `${prefix}-${diagramId.replace(/[^a-zA-Z0-9]/g, "-")}`, [prefix, diagramId]);

  const { mermaidRef, renderError, isRendered, isVisible } = useMermaidRenderer({
    sourceCode,
    entityId: diagramId,
    domId,
  });

  if (renderError !== null) {
    return (
      <div className="text-center p-6 bg-red-50 border border-red-100 rounded-lg max-w-full">
        <div className="text-red-500 text-2xl mb-2">⚠️</div>
        <h4 className="text-red-700 font-bold text-sm">Rendering Error</h4>
        <pre className="mt-2 p-3 bg-gray-100 rounded text-[10px] text-left overflow-auto max-w-full text-red-600">
          {renderError}
        </pre>
      </div>
    );
  }

  return (
    <div className="relative bg-white min-h-48 flex items-center justify-center border border-gray-100 rounded-lg overflow-hidden">
      <div
        ref={mermaidRef}
        key={`${diagramType}-${diagramId}`}
        className={`transition-opacity duration-500 w-full overflow-auto ${
          isRendered ? "opacity-100" : "opacity-0"
        }`}
      />
      
      {!isRendered && !isVisible && (
        <div className="absolute inset-0 flex flex-col items-center justify-center bg-gray-50 text-gray-400">
          <Network className="h-8 w-8 mb-2 opacity-50" />
          <span className="text-xs">Diagram in viewport to render</span>
        </div>
      )}

      {!isRendered && isVisible && (
        <div className="absolute inset-0 flex items-center justify-center text-gray-400 text-sm animate-pulse bg-white">
          <div className="flex flex-col items-center">
            <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mb-2" />
            Generating {diagramType}...
          </div>
        </div>
      )}
    </div>
  );
}


