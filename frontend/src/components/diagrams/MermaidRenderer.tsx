import { useMermaidRenderer } from "./hooks/useMermaidRenderer";

interface MermaidRendererProps {
  readonly diagramId: string;
  readonly sourceCode: string;
  readonly diagramType?: string;
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
}: MermaidRendererProps) {
  const { mermaidRef, renderError, isRendered } = useMermaidRenderer({
    sourceCode,
    diagramId,
  });

  if (renderError !== null) {
    return (
      <div className="text-center p-6 bg-red-50 border border-red-100 rounded-lg">
        <div className="text-red-500 text-2xl mb-2">⚠️</div>
        <h4 className="text-red-700 font-bold text-sm">Rendering Error</h4>
        <pre className="mt-2 p-3 bg-gray-100 rounded text-[10px] text-left overflow-auto max-w-full text-red-600">
          {renderError}
        </pre>
      </div>
    );
  }

  return (
    <div className="relative bg-white min-h-50 flex items-center justify-center">
      <div
        ref={mermaidRef}
        key={`${diagramType}-${diagramId}`}
        className={`transition-opacity duration-500 w-full overflow-auto ${
          isRendered ? "opacity-100" : "opacity-0"
        }`}
      />
      {!isRendered && (
        <div className="absolute inset-0 flex items-center justify-center text-gray-400 text-sm animate-pulse">
          Generating {diagramType}...
        </div>
      )}
    </div>
  );
}


