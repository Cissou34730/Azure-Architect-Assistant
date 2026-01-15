import { useState, useEffect } from "react";
import { diagramApi } from "../../services/diagramService";
import { DiagramSetResponse } from "../../types/api";
import { DiagramSetHeader } from "./DiagramSetHeader";
import { AmbiguitySection } from "./AmbiguitySection";
import { DiagramGrid } from "./DiagramGrid";
import { normalizeDiagramSet } from "./normalizers";

interface DiagramSetViewerProps {
  readonly diagramSetId: string;
}

function LoadingSpinner() {
  return (
    <div className="flex items-center justify-center p-12">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" />
      <span className="ml-4 text-gray-600 text-lg">Loading diagram set...</span>
    </div>
  );
}

function ErrorDisplay({ message }: { readonly message: string }) {
  return (
    <div className="bg-red-50 border border-red-200 rounded-lg p-6 m-6">
      <div className="flex items-center">
        <svg
          className="h-6 w-6 text-red-500 mr-3"
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
          <h3 className="text-red-800 font-semibold text-lg">
            Error Loading Diagram Set
          </h3>
          <p className="text-red-700 text-sm mt-1">{message}</p>
        </div>
      </div>
    </div>
  );
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

        const data = await diagramApi.getDiagramSet(diagramSetId);
        const normalized = normalizeDiagramSet(data);

        if (normalized === null) {
          setError("Failed to parse diagram set data");
        } else {
          setDiagramSet(normalized);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error occurred");
      } finally {
        setLoading(false);
      }
    };

    void fetchDiagramSet();
  }, [diagramSetId]);

  if (loading) {
    return <LoadingSpinner />;
  }

  if (error !== null) {
    return <ErrorDisplay message={error} />;
  }

  if (diagramSet === null) {
    return null;
  }

  return (
    <div className="space-y-8 p-6">
      <DiagramSetHeader
        id={diagramSet.id}
        adrId={diagramSet.adrId}
        createdAt={diagramSet.createdAt}
        diagramCount={diagramSet.diagrams.length}
      />

      <div className="bg-gray-50 border border-gray-200 rounded-lg p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-3">
          Input Description
        </h2>
        <p className="text-gray-700 whitespace-pre-wrap">
          {diagramSet.inputDescription}
        </p>
      </div>

      <DiagramGrid
        diagrams={diagramSet.diagrams}
      />

      <AmbiguitySection ambiguities={diagramSet.ambiguities} />
    </div>
  );
}
