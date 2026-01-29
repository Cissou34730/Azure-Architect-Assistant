import { Virtuoso } from "react-virtuoso";
import type { CostEstimate } from "../../../../../types/api";
import { Section } from "./Section";
import { CostCard } from "./CostCard";

interface CostsSectionProps {
  readonly costs: readonly CostEstimate[];
  readonly expanded: boolean;
  readonly onToggle: () => void;
  readonly onNavigate?: () => void;
}

export function CostsSection({ costs, expanded, onToggle, onNavigate }: CostsSectionProps) {
  return (
    <Section 
      title="Cost Projections" 
      expanded={expanded}
      onToggle={onToggle}
      count={costs.length}
      onViewAll={onNavigate}
    >
      <div className="h-40">
        <Virtuoso
          data={costs}
          itemContent={(_index, cost) => (
            <div className="pb-2">
              <CostCard 
                estimate={cost}
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
