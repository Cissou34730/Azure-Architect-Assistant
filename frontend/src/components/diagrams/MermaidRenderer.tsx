import { useMemo } from "react";
import { Network } from "lucide-react";
import { useMermaidRenderer } from "./hooks/useMermaidRenderer";

interface MermaidRendererProps {
  readonly diagramId: string; // Entity ID (e.g. diag-123)
  readonly sourceCode: string;
  readonly diagramType?: string;
  readonly prefix?: string; // Optional prefix for DOM uniqueness
  readonly className?: string;
}

/**
 * MermaidRenderer Component
 *
 * Renders a single Mermaid diagram from source code.
 */
function RenderError({ renderError }: { readonly renderError: string }) {
  return (
    <div className="text-center p-6 bg-danger-soft border border-danger-line rounded-lg max-w-full">
      <div className="text-danger text-2xl mb-2">⚠️</div>
      <h4 className="text-danger-strong font-bold text-sm">Rendering Error</h4>
      <pre className="mt-2 p-3 bg-muted rounded text-[10px] text-left overflow-auto max-w-full text-danger">
        {renderError}
      </pre>
    </div>
  );
}

function LoadingState({ diagramType, isVisible }: { readonly diagramType: string; readonly isVisible: boolean }) {
  if (!isVisible) {
    return (
      <div className="absolute inset-0 flex flex-col items-center justify-center bg-surface text-dim">
        <Network className="h-8 w-8 mb-2 opacity-50" />
        <span className="text-xs">Diagram in viewport to render</span>
      </div>
    );
  }
  
  return (
    <div className="absolute inset-0 flex items-center justify-center text-dim text-sm animate-pulse bg-card">
      <div className="flex flex-col items-center">
        <div className="w-8 h-8 border-2 border-brand border-t-transparent rounded-full animate-spin mb-2" />
        Generating {diagramType}...
      </div>
    </div>
  );
}

export default function MermaidRenderer({
  diagramId,
  sourceCode,
  diagramType = "diagram",
  prefix = "render",
  className,
}: MermaidRendererProps) {
  const domId = useMemo(() => `${prefix}-${diagramId.replace(/[^a-zA-Z0-9]/g, "-")}`, [prefix, diagramId]);
  const { mermaidRef, renderError, isRendered, isVisible } = useMermaidRenderer({
    sourceCode,
    entityId: diagramId,
    domId,
  });

  const containerClass = className !== undefined && className !== '' 
    ? className 
    : 'bg-card min-h-96 border border-border rounded-lg';

  if (renderError !== null) {
    return <RenderError renderError={renderError} />;
  }

  return (
    <div className={`relative flex items-center justify-center ${containerClass}`}>
      <div
        ref={mermaidRef}
        key={`${diagramType}-${diagramId}`}
        className={`transition-opacity duration-500 w-full flex items-center justify-center ${
          isRendered ? "opacity-100" : "opacity-0"
        }`}
      />
      {!isRendered && <LoadingState diagramType={diagramType} isVisible={isVisible} />}
    </div>
  );
}




