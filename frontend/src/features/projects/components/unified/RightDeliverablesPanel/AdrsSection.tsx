import type { AdrArtifact } from "../../../../../types/api";
import { Section } from "./Section";
import { DeliverableCard } from "./DeliverableCard";

interface AdrsSectionProps {
  readonly adrs: readonly AdrArtifact[];
  readonly expanded: boolean;
  readonly onToggle: () => void;
  readonly onNavigate?: () => void;
}

export function AdrsSection({ adrs, expanded, onToggle, onNavigate }: AdrsSectionProps) {
  return (
    <Section 
      title="ADR Gallery" 
      expanded={expanded}
      onToggle={onToggle}
      count={adrs.length}
      onViewAll={onNavigate}
    >
      <div className="space-y-2">
        {adrs.slice(0, 3).map((adr) => (
          <DeliverableCard 
            key={adr.id}
            artifact={adr}
            onClick={onNavigate ?? (() => { /* No-op */ })}
          />
        ))}
        {adrs.length > 3 && (
          <button 
            onClick={onNavigate}
            className="w-full py-2 border-t border-gray-50 text-[11px] font-medium text-blue-600 hover:text-blue-700"
          >
            View all {adrs.length} ADRs
          </button>
        )}
      </div>
    </Section>
  );
}
