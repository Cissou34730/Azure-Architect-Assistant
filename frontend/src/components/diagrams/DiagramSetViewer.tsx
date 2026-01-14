import { useState, useEffect } from "react";
import MermaidRenderer from "./MermaidRenderer";
import { diagramApi } from "../../services/apiService";

interface DiagramSetViewerProps {
  diagramSetId: string;
}

interface DiagramData {
  id: string;
  diagram_type: string;
  source_code: string;
  version: string;
  created_at: string;
}

interface Ambiguity {
  id: string;
  resolved: boolean;
  ambiguous_text?: string;
  suggested_clarification?: string;
}

interface DiagramSetResponse {
  id: string;
  adr_id?: string;
  input_description: string;
  diagrams: DiagramData[];
  ambiguities: Ambiguity[];
  created_at: string;
  updated_at: string;
}

export function DiagramSetViewer({ diagramSetId }: DiagramSetViewerProps) {
  const [diagramSet, setDiagramSet] = useState<DiagramSetResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchDiagramSet = async () => {
      try {
        setLoading(true);
        setError(null);

        const data: DiagramSetResponse = await diagramApi.getDiagramSet(diagramSetId);
        // Ensure ambiguities is always an array of the right shape
        data.ambiguities = Array.isArray(data.ambiguities) ? data.ambiguities.map((a) => ({
          id: String((a as unknown).id ?? ""),
          resolved: Boolean((a as unknown).resolved),
          ambiguous_text: (a as unknown).ambiguous_text ?? (a as unknown).text_fragment ?? undefined,
          suggested_clarification: (a as unknown).suggested_clarification ?? undefined,
        })) : [];

        setDiagramSet(data);
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : "Unknown error occurred";
        setError(errorMessage);
        console.error("Error fetching diagram set:", err);
      } finally {
        setLoading(false);
      }
    };

    void fetchDiagramSet();
  }, [diagramSetId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center p-12">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" />
        <span className="ml-4 text-gray-600 text-lg">Loading diagram set...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6 m-6">
        <div className="flex items-center">
          <svg className="h-6 w-6 text-red-500 mr-3" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
          </svg>
          <div>
            <h3 className="text-red-800 font-semibold text-lg">Error Loading Diagram Set</h3>
            <p className="text-red-700 text-sm mt-1">{error}</p>
          </div>
        </div>
      </div>
    );
  }

  if (!diagramSet) return null;

  const diagramTypeLabels: Record<string, string> = {
    mermaid_functional: "Functional Flow",
    c4_context: "C4 Context (System Boundaries)",
    c4_container: "C4 Container (Application Architecture)",
  };

  const availableDiagrams = diagramSet.diagrams.map((d) => d.diagram_type);

  return (
    <div className="space-y-8 p-6">
      <div className="border-b border-gray-200 pb-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Architecture Diagrams</h1>
        <div className="flex items-center gap-4 text-sm text-gray-600">
          <span>Diagram Set ID: {diagramSet.id}</span>
          {diagramSet.adr_id && <span>ADR: {diagramSet.adr_id}</span>}
          <span>Created: {new Date(diagramSet.created_at).toLocaleDateString()}</span>
          <span className="font-medium text-blue-600">{availableDiagrams.length} diagrams</span>
        </div>
      </div>

      <div className="bg-gray-50 border border-gray-200 rounded-lg p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-3">Input Description</h2>
        <p className="text-gray-700 whitespace-pre-wrap">{diagramSet.input_description}</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
        {availableDiagrams.map((diagramType) => (
          <div key={diagramType} className="border border-gray-300 rounded-lg bg-white shadow-sm">
            <div className="bg-linear-to-r from-blue-600 to-blue-700 text-white px-6 py-4 rounded-t-lg">
              <h3 className="text-lg font-semibold">{diagramTypeLabels[diagramType] || diagramType}</h3>
            </div>

            <div className="p-4">
              <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
                <DiagramCard diagramSetId={diagramSetId} diagramType={diagramType} />
              </div>
            </div>
          </div>
        ))}
      </div>

      {Array.isArray(diagramSet.ambiguities) && diagramSet.ambiguities.length > 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 mt-8">
          <h2 className="text-xl font-semibold text-yellow-900 mb-4">Detected Ambiguities ({diagramSet.ambiguities.length})</h2>
          <div className="space-y-3">
            {diagramSet.ambiguities.map((ambiguity) => (
              <div key={ambiguity.id} className={`bg-white border rounded-lg p-4 ${ambiguity.resolved ? "border-green-300" : "border-yellow-300"}`}>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-xs font-medium px-2 py-1 rounded bg-yellow-100 text-yellow-800">AMBIGUITY</span>
                      {ambiguity.resolved && (
                        <span className="text-xs font-medium px-2 py-1 rounded bg-green-100 text-green-800">RESOLVED</span>
                      )}
                    </div>
                    {ambiguity.ambiguous_text && <p className="text-gray-800 mb-2 font-medium">{ambiguity.ambiguous_text}</p>}
                    {ambiguity.suggested_clarification && (
                      <p className="text-sm text-gray-600 bg-blue-50 p-3 rounded border border-blue-200">
                        <strong>Suggested:</strong> {ambiguity.suggested_clarification}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

interface DiagramCardProps {
  diagramSetId: string;
  diagramType: string;
}

function DiagramCard({ diagramSetId, diagramType }: DiagramCardProps) {
  const [diagram, setDiagram] = useState<DiagramData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchDiagram = async () => {
      try {
        setLoading(true);
        const data: DiagramSetResponse = await diagramApi.getDiagramSet(diagramSetId);
        const foundDiagram = data.diagrams.find((d) => d.diagram_type === diagramType);
        setDiagram(foundDiagram || null);
      } catch (err) {
        console.error("Error fetching diagram:", err);
      } finally {
        setLoading(false);
      }
    };

    void fetchDiagram();
  }, [diagramSetId, diagramType]);

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  if (!diagram) {
    return (
      <div className="p-4 text-center text-gray-500">
        <p>Diagram not available</p>
      </div>
    );
  }

  return (
    <div className="p-4">
      <MermaidRenderer diagramSetId={diagramSetId} diagramType={diagramType} />
    </div>
  );
}
