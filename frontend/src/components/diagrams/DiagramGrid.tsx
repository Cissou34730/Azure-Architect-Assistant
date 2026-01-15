import MermaidRenderer from "./MermaidRenderer";
import { DiagramData } from "../../types/api";

const DIAGRAM_TYPE_LABELS: Record<string, string> = {
  mermaidFunctional: "Functional Flow",
  c4Context: "C4 Context (System Boundaries)",
  c4Container: "C4 Container (Application Architecture)",
};

interface DiagramGridProps {
  readonly diagrams: readonly DiagramData[];
}

export function DiagramGrid({ diagrams }: DiagramGridProps) {
  if (diagrams.length === 0) {
    return (
      <div className="bg-white border border-gray-200 rounded-lg p-12 text-center text-gray-500">
        <p className="text-lg italic">No diagrams available to display.</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
      {diagrams.map((diagram) => (
        <div
          key={diagram.id}
          className="border border-gray-300 rounded-lg bg-white shadow-sm hover:shadow-md transition-shadow"
        >
          <div className="bg-linear-to-r from-blue-600 to-blue-700 text-white px-6 py-4 rounded-t-lg">
            <h3 className="text-lg font-semibold">
              {DIAGRAM_TYPE_LABELS[diagram.diagramType] ?? diagram.diagramType}
            </h3>
          </div>

          <div className="p-4">
            <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
              <div className="p-4">
                <MermaidRenderer
                  diagramId={diagram.id}
                  sourceCode={diagram.sourceCode}
                  diagramType={diagram.diagramType}
                />
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
