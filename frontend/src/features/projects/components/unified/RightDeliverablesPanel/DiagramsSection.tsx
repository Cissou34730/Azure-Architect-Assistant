import { LayoutGrid } from "lucide-react";
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
      <div className="grid grid-cols-1 gap-2.5">
        {diagrams.slice(0, 3).map((diagram, idx) => (
          <DiagramPreviewCard 
            key={diagram.id !== "" ? diagram.id : `diag-${idx}`}
            diagram={diagram}
            onClick={onNavigate ?? (() => { /* No-op */ })}
          />
        ))}
        {diagrams.length === 0 && (
          <EmptyState 
            icon={<LayoutGrid className="h-8 w-8 text-gray-200" />}
            message="No diagrams generated"
            actionLabel="Generate Diagram"
            onClick={onNavigate ?? (() => { /* No-op */ })}
          />
        )}
        {diagrams.length > 3 && (
          <button
            onClick={onNavigate}
            className="w-full text-center text-sm text-blue-600 hover:text-blue-700 py-2"
          >
            +{diagrams.length - 3} more diagrams
          </button>
        )}
      </div>
    </Section>
  );
}
