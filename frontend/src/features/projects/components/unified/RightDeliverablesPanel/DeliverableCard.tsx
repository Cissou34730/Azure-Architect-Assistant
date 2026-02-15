import { FileText, AlertCircle } from "lucide-react";
import type { AdrArtifact, FindingArtifact } from "../../../../../types/api";
import { Badge } from "../../../../../components/common";
import { BaseCard } from "./BaseCard";

interface DeliverableCardProps {
  readonly artifact: AdrArtifact | FindingArtifact;
  readonly onClick: () => void;
}

export function DeliverableCard({ artifact, onClick }: DeliverableCardProps) {
  const isFinding = "severity" in artifact;
  const dateStr = artifact.createdAt !== undefined 
    ? new Date(artifact.createdAt).toLocaleDateString() 
    : "Recent";
  
  return (
    <BaseCard
      title={artifact.title}
      date={dateStr}
      onClick={onClick}
    >
      <div className="flex items-center gap-2">
        {isFinding ? (
          <>
            <Badge
              variant={artifact.severity === "high" || artifact.severity === "critical" ? "error" : artifact.severity === "medium" ? "warning" : "success"}
              size="sm"
            >
              <AlertCircle className="h-3 w-3 mr-1" />
              {artifact.severity}
            </Badge>
            {artifact.wafPillar !== undefined && artifact.wafPillar !== "" && (
              <>
                <span className="text-[10px] text-dim">•</span>
                <span className="text-[10px] bg-muted text-secondary px-1 rounded">{artifact.wafPillar}</span>
              </>
            )}
          </>
        ) : (
          <>
            <Badge variant="info" size="sm">
              <FileText className="h-3 w-3 mr-1" />
              ADR
            </Badge>
            <span className="text-[10px] text-dim">•</span>
            <span className="text-[10px] bg-muted text-secondary px-1 rounded uppercase">{artifact.status}</span>
          </>
        )}
      </div>
    </BaseCard>
  );
}

