import { useState } from "react";
import { Code } from "lucide-react";
import { EmptyState } from "../../../../shared/ui";
import type { IacArtifact } from "../../types/api-artifacts";
import { ArtifactSelector, ArtifactBoard } from "./IacViewerParts";

interface IacViewerProps {
  readonly iacArtifacts: readonly IacArtifact[];
}

export function IacViewer({ iacArtifacts }: IacViewerProps) {
  const [selectedArtifact, setSelectedArtifact] = useState(
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
            className="bg-brand text-inverse px-4 py-2 rounded-lg hover:bg-brand-strong transition-colors text-sm"
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



