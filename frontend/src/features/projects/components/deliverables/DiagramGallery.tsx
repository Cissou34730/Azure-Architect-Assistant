import { useState } from "react";
import { Network, X, Download, ZoomIn } from "lucide-react";
import { Card, CardContent, Badge, EmptyState } from "../../../../components/common";
import MermaidRenderer from "../../../../components/diagrams/MermaidRenderer";

interface Diagram {
  readonly id?: string;
  readonly title?: string;
  readonly type?: string;
  readonly mermaidSource?: string;
  readonly createdAt?: string;
}

interface DiagramGalleryProps {
  diagrams: readonly Diagram[];
}

type DiagramFilter = "all" | "c4-context" | "c4-container" | "functional";

export function DiagramGallery({ diagrams }: DiagramGalleryProps) {
  const [filter, setFilter] = useState<DiagramFilter>("all");
  const [selectedDiagram, setSelectedDiagram] = useState<Diagram | null>(null);

  const filters: { id: DiagramFilter; label: string }[] = [
    { id: "all", label: "All" },
    { id: "c4-context", label: "C4 Context" },
    { id: "c4-container", label: "C4 Container" },
    { id: "functional", label: "Functional" },
  ];

  const filteredDiagrams = diagrams.filter((diagram) => {
    if (filter === "all") return true;
    const type = (diagram.type || "").toLowerCase();
    return type.includes(filter);
  });

  if (diagrams.length === 0) {
    return (
      <EmptyState
        icon={Network}
        title="No diagrams yet"
        description="Generate architecture diagrams using the Workspace chat"
        action={
          <button className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors text-sm">
            Go to Workspace
          </button>
        }
      />
    );
  }

  return (
    <div className="space-y-6">
      {/* Filter Chips */}
      <div className="flex flex-wrap gap-2">
        {filters.map((f) => (
          <button
            key={f.id}
            onClick={() => setFilter(f.id)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              filter === f.id
                ? "bg-blue-600 text-white"
                : "bg-gray-100 text-gray-700 hover:bg-gray-200"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Diagram Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredDiagrams.map((diagram) => (
          <Card
            key={diagram.id || diagram.title}
            hover
            onClick={() => setSelectedDiagram(diagram)}
          >
            <CardContent className="p-4">
              <div className="aspect-video bg-gray-50 rounded-lg mb-3 overflow-hidden relative group">
                {diagram.mermaidSource ? (
                  <>
                    <MermaidRenderer diagramId={diagram.id || `diagram-preview-${diagram.title}`} sourceCode={diagram.mermaidSource} />
                    <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-10 transition-all flex items-center justify-center">
                      <ZoomIn className="h-8 w-8 text-white opacity-0 group-hover:opacity-100 transition-opacity" />
                    </div>
                  </>
                ) : (
                  <div className="flex items-center justify-center h-full text-gray-400">
                    <Network className="h-12 w-12" />
                  </div>
                )}
              </div>

              <div className="space-y-2">
                <div className="flex items-start justify-between gap-2">
                  <h3 className="font-medium text-gray-900 text-sm line-clamp-2">
                    {diagram.title || "Untitled Diagram"}
                  </h3>
                  {diagram.type && (
                    <Badge variant="primary" size="sm">
                      {diagram.type}
                    </Badge>
                  )}
                </div>

                {diagram.createdAt && (
                  <p className="text-xs text-gray-500">
                    {new Date(diagram.createdAt).toLocaleDateString()}
                  </p>
                )}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Full Screen Modal */}
      {selectedDiagram && (
        <DiagramModal
          diagram={selectedDiagram}
          onClose={() => setSelectedDiagram(null)}
        />
      )}
    </div>
  );
}

function DiagramModal({ diagram, onClose }: { diagram: Diagram; onClose: () => void }) {
  const handleDownloadSVG = () => {
    // Implementation would export the rendered SVG
    alert("Download SVG - Feature coming soon");
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-75 p-4">
      <div className="bg-white rounded-lg max-w-6xl w-full max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">
              {diagram.title || "Untitled Diagram"}
            </h2>
            {diagram.type && (
              <Badge variant="primary" size="sm" className="mt-1">
                {diagram.type}
              </Badge>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleDownloadSVG}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              aria-label="Download"
            >
              <Download className="h-5 w-5 text-gray-600" />
            </button>
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              aria-label="Close"
            >
              <X className="h-5 w-5 text-gray-600" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-6">
          {diagram.mermaidSource ? (
            <div className="flex items-center justify-center min-h-full">
              <MermaidRenderer diagramId={`modal-${diagram.id || diagram.title}`} sourceCode={diagram.mermaidSource} />
            </div>
          ) : (
            <div className="flex items-center justify-center h-full text-gray-400">
              <p>No diagram source available</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
