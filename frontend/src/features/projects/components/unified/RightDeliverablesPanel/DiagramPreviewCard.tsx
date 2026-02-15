import { Share2 } from "lucide-react";
import type { DiagramData } from "../../../../../types/api";
import { BaseCard } from "./BaseCard";

interface DiagramPreviewCardProps {
  readonly diagram: DiagramData;
  readonly onClick: () => void;
}

export function DiagramPreviewCard({ diagram, onClick }: DiagramPreviewCardProps) {
  return (
    <BaseCard
      title={`${diagram.diagramType} Diagram`}
      date={new Date(diagram.createdAt).toLocaleDateString()}
      onClick={onClick}
    >
      <div className="relative aspect-video rounded-md border border-border bg-surface flex items-center justify-center overflow-hidden">
        <Share2 className="h-6 w-6 text-border" />
        <div className="absolute inset-0 bg-brand/0 group-hover:bg-brand/10 transition-colors flex items-center justify-center">
          <span className="opacity-0 group-hover:opacity-100 text-[10px] font-medium text-brand-strong bg-card shadow-sm px-2 py-1 rounded">
            Preview {diagram.diagramType}
          </span>
        </div>
      </div>
    </BaseCard>
  );
}

