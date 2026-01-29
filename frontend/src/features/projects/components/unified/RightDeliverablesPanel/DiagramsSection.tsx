import { LayoutGrid } from "lucide-react";
import { Virtuoso } from "react-virtuoso";
import type { DiagramData } from "../../../../../types/api";
import { Section } from "./Section";
import { DiagramPreviewCard } from "./DiagramPreviewCard";
import { EmptyState } from "./EmptyState";

interface DiagramsSectionProps {
  readonly diagrams: readonly DiagramData[];
  readonly expanded: boolean;
  readonly onToggle: () => void;
  readonly onNavigate?: () => void;
}

export function DiagramsSection({ diagrams, expanded, onToggle, onNavigate }: DiagramsSectionProps) {
  return (
    <Section 
      title="Architectural Diagrams" 
      expanded={expanded}
      onToggle={onToggle}
      count={diagrams.length}
      onViewAll={onNavigate}
    >
      <div className="h-64">
        {diagrams.length === 0 ? (
          <EmptyState 
            icon={<LayoutGrid className="h-8 w-8 text-gray-200" />}
            message="No diagrams generated"
            actionLabel="Generate Diagram"
            onClick={onNavigate ?? (() => { /* No-op */ })}
          />
        ) : (
          <Virtuoso
            data={diagrams}
            itemContent={(index, diagram) => (
              <div className="pb-2.5">
                <DiagramPreviewCard 
                  key={diagram.id !== "" ? diagram.id : `diag-${index}`}
                  diagram={diagram}
                  onClick={onNavigate ?? (() => { /* No-op */ })}
                />
              </div>
            )}
            style={{ height: "100%" }}
          />
        )}
      </div>
    </Section>
  );
}
