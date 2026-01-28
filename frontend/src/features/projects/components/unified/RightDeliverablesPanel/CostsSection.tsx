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
      <div className="space-y-2">
        {costs.map((cost) => (
          <CostCard 
            key={cost.id}
            estimate={cost}
            onClick={onNavigate ?? (() => { /* No-op */ })}
          />
        ))}
      </div>
    </Section>
  );
}
