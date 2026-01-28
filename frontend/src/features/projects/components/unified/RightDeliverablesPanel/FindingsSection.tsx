import type { FindingArtifact } from "../../../../../types/api";
import { Section } from "./Section";
import { DeliverableCard } from "./DeliverableCard";

interface FindingsSectionProps {
  readonly findings: readonly FindingArtifact[];
  readonly expanded: boolean;
  readonly onToggle: () => void;
}

export function FindingsSection({ findings, expanded, onToggle }: FindingsSectionProps) {
  return (
    <Section 
      title="Gap Analysis & Findings" 
      expanded={expanded}
      onToggle={onToggle}
      count={findings.length}
    >
      <div className="space-y-2">
        {findings.slice(0, 3).map((finding) => (
          <DeliverableCard 
            key={finding.id}
            artifact={finding}
            onClick={() => { /* No-op */ }}
          />
        ))}
      </div>
    </Section>
  );
}
