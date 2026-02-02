import { useState, useMemo } from "react";
import { VirtuosoGrid } from "react-virtuoso";
import { Network, X, Download, ZoomIn, ZoomOut, Maximize2 } from "lucide-react";
import { Card, CardContent, Badge, EmptyState } from "../../../../components/common";
import MermaidRenderer from "../../../../components/diagrams/MermaidRenderer";
import type { DiagramData } from "../../../../types/api";

const VIRTUALIZE_THRESHOLD = 9;

interface DiagramGalleryProps {
  readonly diagrams: readonly DiagramData[];
}

type DiagramFilter = "all" | "c4-context" | "c4-container" | "functional";

interface FilterChipsProps {
  readonly currentFilter: DiagramFilter;
  readonly onFilterChange: (filter: DiagramFilter) => void;
}

function FilterChips({ currentFilter, onFilterChange }: FilterChipsProps) {
  const filters: readonly { id: DiagramFilter; label: string }[] = [
    { id: "all", label: "All" },
    { id: "c4-context", label: "C4 Context" },
    { id: "c4-container", label: "C4 Container" },
    { id: "functional", label: "Functional" },
  ];

  return (
    <div className="flex flex-wrap gap-2">
      {filters.map((f) => (
        <button
          key={f.id}
          type="button"
          onClick={() => {
            onFilterChange(f.id);
          }}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            currentFilter === f.id
              ? "bg-blue-600 text-white"
              : "bg-gray-100 text-gray-700 hover:bg-gray-200"
          }`}
        >
          {f.label}
        </button>
      ))}
    </div>
  );
}

interface DiagramCardProps {
  readonly diagram: DiagramData;
  readonly onClick: (diagram: DiagramData) => void;
}

function DiagramCard({ diagram, onClick }: DiagramCardProps) {
  const safeSource = getSafeString(diagram.sourceCode).trim();
  return (
    <Card
      hover
      onClick={() => {
        onClick(diagram);
      }}
    >
      <CardContent className="p-4">
        <div className="aspect-video bg-gray-50 rounded-lg mb-3 overflow-hidden relative group">
          {safeSource !== "" ? (
            <>
              <MermaidRenderer
                diagramId={diagram.id}
                prefix="preview"
                sourceCode={safeSource}
              />
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
              {diagram.diagramType}
            </h3>
            <Badge variant="primary" size="sm">
              {diagram.version}
            </Badge>
          </div>

          <p className="text-xs text-gray-500">
            {new Date(diagram.createdAt).toLocaleDateString()}
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

interface DiagramModalProps {
  readonly diagram: DiagramData;
  readonly onClose: () => void;
}

function useZoomControls() {
  const [zoom, setZoom] = useState(100);
  
  const handleZoomIn = () => {
    setZoom((prev) => Math.min(prev + 25, 300));
  };

  const handleZoomOut = () => {
    setZoom((prev) => Math.max(prev - 25, 50));
  };

  const handleResetZoom = () => {
    setZoom(100);
  };
  
  return { zoom, handleZoomIn, handleZoomOut, handleResetZoom };
}

function DiagramModal({ diagram, onClose }: DiagramModalProps) {
  const safeSource = getSafeString(diagram.sourceCode).trim();
  const { zoom, handleZoomIn, handleZoomOut, handleResetZoom } = useZoomControls();
  
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
              {diagram.diagramType}
            </h2>
            <Badge variant="primary" size="sm" className="mt-1">
              Version: {diagram.version}
            </Badge>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleZoomOut}
              disabled={zoom <= 50}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              aria-label="Zoom Out"
            >
              <ZoomOut className="h-5 w-5 text-gray-600" />
            </button>
            <span className="text-sm font-medium text-gray-600 min-w-12 text-center">
              {zoom}%
            </span>
            <button
              type="button"
              onClick={handleZoomIn}
              disabled={zoom >= 300}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              aria-label="Zoom In"
            >
              <ZoomIn className="h-5 w-5 text-gray-600" />
            </button>
            <button
              type="button"
              onClick={handleResetZoom}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              aria-label="Reset Zoom"
            >
              <Maximize2 className="h-5 w-5 text-gray-600" />
            </button>
            <div className="w-px h-6 bg-gray-300 mx-1" />
            <button
              type="button"
              onClick={handleDownloadSVG}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              aria-label="Download"
            >
              <Download className="h-5 w-5 text-gray-600" />
            </button>
            <button
              type="button"
              onClick={onClose}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              aria-label="Close"
            >
              <X className="h-5 w-5 text-gray-600" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto bg-white">
          {safeSource !== "" ? (
            <div 
              className="w-full h-full flex items-center justify-center p-6"
              style={{ transform: `scale(${zoom / 100})`, transformOrigin: 'center', transition: 'transform 0.2s ease' }}
            >
              <MermaidRenderer
                diagramId={diagram.id}
                prefix="modal"
                sourceCode={safeSource}
                className="w-full h-full"
              />
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

export function DiagramGallery({ diagrams }: DiagramGalleryProps) {
  const [filter, setFilter] = useState<DiagramFilter>("all");
  const [selectedDiagram, setSelectedDiagram] = useState<DiagramData | null>(null);

  const filteredDiagrams = useMemo(() => {
    return diagrams.filter((diagram) => {
      if (filter === "all") return true;
      const type = getSafeString(diagram.diagramType).toLowerCase();
      // Backend uses: mermaid_functional, c4_context, c4_container
      // Filter IDs use: functional, c4-context, c4-container
      if (filter === "functional") return type.includes("functional");
      if (filter === "c4-context") return type === "c4_context";
      return type === "c4_container";
    });
  }, [diagrams, filter]);

  // Task 4.6: Memoize sorted diagrams
  const sortedDiagrams = useMemo(() => {
    return [...filteredDiagrams].sort((a, b) => {
      const dateA = getSafeString(a.createdAt);
      const dateB = getSafeString(b.createdAt);
      return dateB.localeCompare(dateA);
    });
  }, [filteredDiagrams]);

  if (diagrams.length === 0) {
    return (
      <EmptyState
        icon={Network}
        title="No diagrams yet"
        description="Generate architecture diagrams using the Workspace chat"
        action={
          <button
            type="button"
            className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors text-sm"
          >
            Go to Workspace
          </button>
        }
      />
    );
  }

  return (
    <div className="space-y-6">
      <FilterChips currentFilter={filter} onFilterChange={setFilter} />

      {sortedDiagrams.length > VIRTUALIZE_THRESHOLD ? (
        <VirtuosoGrid
          useWindowScroll
          data={sortedDiagrams}
          overscan={400}
          listClassName="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
          itemContent={(_index, diagram) => (
            <DiagramCard
              key={diagram.id}
              diagram={diagram}
              onClick={setSelectedDiagram}
            />
          )}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {sortedDiagrams.map((diagram) => (
            <DiagramCard
              key={diagram.id}
              diagram={diagram}
              onClick={setSelectedDiagram}
            />
          ))}
        </div>
      )}

      {selectedDiagram !== null && (
        <DiagramModal
          diagram={selectedDiagram}
          onClose={() => {
            setSelectedDiagram(null);
          }}
        />
      )}
    </div>
  );
}

function getSafeString(value: string | undefined): string {
  return typeof value === "string" ? value : "";
}

