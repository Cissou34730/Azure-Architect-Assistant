import { useState } from "react";
import { Code } from "lucide-react";
import { EmptyState } from "../../../../components/common";
import type { IacArtifact } from "../../../../types/api";
import { ArtifactSelector, ArtifactBoard } from "./IacViewerParts";

interface IacViewerProps {
  readonly iacArtifacts: readonly IacArtifact[];
}

export function IacViewer({ iacArtifacts }: IacViewerProps) {
  const [selectedArtifact, setSelectedArtifact] = useState<IacArtifact | null>(
    iacArtifacts.length > 0 ? (iacArtifacts[0] ?? null) : null,
  );
  const [selectedFileIndex, setSelectedFileIndex] = useState(0);

  if (iacArtifacts.length === 0) {
    return (
      <EmptyState
        icon={Code}
        title="No IaC artifacts yet"
        description="Generate Infrastructure as Code using the Workspace chat"
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
      <ArtifactSelector
        artifacts={iacArtifacts}
        selectedId={selectedArtifact?.id}
        onSelect={(artifact) => {
          setSelectedArtifact(artifact);
          setSelectedFileIndex(0);
        }}
      />

      {selectedArtifact !== null && (
        <ArtifactBoard
          selectedArtifact={selectedArtifact}
          selectedFileIndex={selectedFileIndex}
          onFileSelect={setSelectedFileIndex}
        />
      )}
    </div>
  );
}
