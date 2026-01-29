import { Virtuoso } from "react-virtuoso";
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
      <div className="h-48">
        <Virtuoso
          data={findings}
          itemContent={(_index, finding) => (
            <div className="pb-2">
              <DeliverableCard 
                artifact={finding}
                onClick={() => { /* No-op */ }}
              />
            </div>
          )}
          style={{ height: "100%" }}
        />
      </div>
    </Section>
  );
}
