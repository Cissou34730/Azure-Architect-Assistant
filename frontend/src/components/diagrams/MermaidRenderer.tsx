import { useEffect, useRef, useState } from "react";
import mermaid from "mermaid";
import { diagramApi } from "../../services/apiService";

interface MermaidRendererProps {
  diagramSetId: string;
  diagramType: string;
}

interface DiagramData {
  id: string;
  diagram_type: string;
  source_code: string;
  version: string;
  created_at: string;
}

interface AmbiguityData {
  id: string;
  category: string;
  description: string;
  severity: string;
  text_fragment: string;
  resolved: boolean;
  resolved_at?: string;
}

interface DiagramSetResponse {
  id: string;
  project_id?: string;
  adr_id?: string;
  input_description: string;
  diagrams: DiagramData[];
  ambiguities: AmbiguityData[];
  created_at: string;
  updated_at: string;
}

/**
 * MermaidRenderer Component
 *
 * Renders Mermaid diagrams by fetching diagram set data from the backend API
 * and using mermaid.js for client-side rendering.
 *
 * Features:
 * - Fetches diagram data from /api/v1/diagram-sets/{id}
 * - Client-side Mermaid rendering with error handling
 * - Displays ambiguities list if any detected
 * - TailwindCSS v4 styling
 *
 * @param diagramSetId - ID of the diagram set to render
 * @param diagramType - Type of diagram to display (e.g., 'functional', 'c4-context')
 */
export default function MermaidRenderer({
  diagramSetId,
  diagramType,
}: MermaidRendererProps) {
  const [diagramSet, setDiagramSet] = useState<DiagramSetResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [renderError, setRenderError] = useState<string | null>(null);
  const mermaidRef = useRef<HTMLDivElement>(null);
  const [isRendered, setIsRendered] = useState(false);

  // Initialize mermaid with configuration once
  useEffect(() => {
    mermaid.initialize({
      startOnLoad: false,
      theme: "default",
      securityLevel: "loose",
      fontFamily: "ui-sans-serif, system-ui, sans-serif",
    });
  }, []);

  // Fetch diagram set data from backend
  useEffect(() => {
    let isMounted = true;
    const fetchDiagramSet = async () => {
      try {
        setLoading(true);
        setError(null);

        const data: DiagramSetResponse =
          await diagramApi.getDiagramSet(diagramSetId);
        if (isMounted) {
          setDiagramSet(data);
        }
      } catch (err) {
        if (isMounted) {
          const errorMessage =
            err instanceof Error ? err.message : "Unknown error occurred";
          setError(errorMessage);
          console.error("Error fetching diagram set:", err);
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    void fetchDiagramSet();
    return () => {
      isMounted = false;
    };
  }, [diagramSetId]);

  // Render the mermaid diagram
  useEffect(() => {
    if (!diagramSet || !mermaidRef.current || isRendered) {
      return;
    }

    let isMounted = true;
    const diagram = diagramSet.diagrams.find(
      (d) => d.diagram_type === diagramType,
    );
    if (!diagram) {
      setRenderError(`Diagram type '${diagramType}' not found in diagram set`);
      return;
    }

    const renderDiagram = async () => {
      try {
        setRenderError(null);

        // Generate unique ID for this diagram
        const diagramId = `mermaid-${diagramSetId}-${diagramType.replace(/[^a-zA-Z0-9]/g, "-")}`;

        // Render the diagram
        const { svg } = await mermaid.render(diagramId, diagram.source_code);

        if (isMounted && mermaidRef.current) {
          mermaidRef.current.innerHTML = svg;
          setIsRendered(true);
        }
      } catch (err) {
        if (isMounted) {
          const errorMessage =
            err instanceof Error ? err.message : "Unknown rendering error";
          setRenderError(`Failed to render Mermaid diagram: ${errorMessage}`);
          console.error("Mermaid rendering error:", err);

          if (mermaidRef.current) {
            mermaidRef.current.innerHTML = `
              <pre class="bg-red-50 border border-red-200 rounded-lg p-4 text-red-800 text-sm overflow-x-auto">
  ${diagram.source_code}
              </pre>
            `;
          }
        }
      }
    };

    void renderDiagram();
    return () => {
      isMounted = false;
    };
  }, [diagramSet, diagramType, diagramSetId, isRendered]);

  // Re-render when diagram set or type changes
  useEffect(() => {
    setIsRendered(false);
  }, [diagramSet, diagramType, diagramSetId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
        <span className="ml-3 text-gray-600">Loading diagram...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <div className="flex items-center">
          <svg
            className="h-5 w-5 text-red-500 mr-2"
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
              clipRule="evenodd"
            />
          </svg>
          <div>
            <h3 className="text-red-800 font-medium">Error Loading Diagram</h3>
            <p className="text-red-700 text-sm mt-1">{error}</p>
          </div>
        </div>
      </div>
    );
  }

  if (!diagramSet) {
    return null;
  }

  const currentDiagram = diagramSet.diagrams.find(
    (d) => d.diagram_type === diagramType,
  );

  return (
    <div className="space-y-6">
      {/* Diagram Header */}
      <div className="border-b border-gray-200 pb-4">
        <h2 className="text-2xl font-semibold text-gray-900">
          {diagramType
            .split("-")
            .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
            .join(" ")}{" "}
          Diagram
        </h2>
        {currentDiagram && (
          <p className="text-sm text-gray-500 mt-1">
            Version {currentDiagram.version} • Created{" "}
            {new Date(currentDiagram.created_at).toLocaleDateString()}
          </p>
        )}
      </div>

      {/* Render Error Message */}
      {renderError && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <div className="flex items-center">
            <svg
              className="h-5 w-5 text-yellow-500 mr-2"
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path
                fillRule="evenodd"
                d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                clipRule="evenodd"
              />
            </svg>
            <div>
              <h3 className="text-yellow-800 font-medium">Rendering Error</h3>
              <p className="text-yellow-700 text-sm mt-1">{renderError}</p>
            </div>
          </div>
        </div>
      )}

      {/* Mermaid Diagram */}
      <div className="bg-white border border-gray-200 rounded-lg p-6 overflow-x-auto">
        <div
          ref={mermaidRef}
          className="flex justify-center items-center min-h-[200px]"
        />
      </div>

      {/* Ambiguities List */}
      {diagramSet.ambiguities.length > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
          <h3 className="text-lg font-medium text-blue-900 mb-4">
            Detected Ambiguities ({diagramSet.ambiguities.length})
          </h3>
          <div className="space-y-3">
            {diagramSet.ambiguities.map((ambiguity) => (
              <div
                key={ambiguity.id}
                className={`bg-white border rounded-lg p-4 ${
                  ambiguity.resolved ? "border-green-300" : "border-blue-300"
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <span
                        className={`text-xs font-medium px-2 py-1 rounded ${
                          ambiguity.severity === "high"
                            ? "bg-red-100 text-red-800"
                            : ambiguity.severity === "medium"
                              ? "bg-yellow-100 text-yellow-800"
                              : "bg-blue-100 text-blue-800"
                        }`}
                      >
                        {ambiguity.severity.toUpperCase()}
                      </span>
                      <span className="text-xs text-gray-500">
                        {ambiguity.category}
                      </span>
                      {ambiguity.resolved && (
                        <span className="text-xs font-medium px-2 py-1 rounded bg-green-100 text-green-800">
                          RESOLVED
                        </span>
                      )}
                    </div>
                    <p className="text-gray-800 mb-2">
                      {ambiguity.description}
                    </p>
                    {ambiguity.text_fragment && (
                      <p className="text-sm text-gray-600 italic bg-gray-50 p-2 rounded border border-gray-200">
                        &quot;{ambiguity.text_fragment}&quot;
                      </p>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Input Description */}
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-3">
          Input Description
        </h3>
        <p className="text-gray-700 whitespace-pre-wrap">
          {diagramSet.input_description}
        </p>
      </div>
    </div>
  );
}
