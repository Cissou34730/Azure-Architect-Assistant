import { Virtuoso } from "react-virtuoso";
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
      <div className="h-48">
        <Virtuoso
          data={adrs}
          itemContent={(_index, adr) => (
            <div className="pb-2">
              <DeliverableCard 
                artifact={adr}
                onClick={onNavigate ?? (() => { /* No-op */ })}
              />
            </div>
          )}
          style={{ height: "100%" }}
        />
      </div>
    </Section>
  );
}
