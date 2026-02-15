import { ProjectState } from "../../../types/agent";
import { StateSection, StateField } from "./StateShared";

interface ContextSectionProps {
  readonly context: NonNullable<ProjectState["context"]>;
}

export function ContextSection({ context }: ContextSectionProps) {
  return (
    <StateSection icon="📝" title="Context">
      {context.summary !== undefined && context.summary !== "" && (
        <StateField label="Summary">
          <p className="text-secondary mt-1">{context.summary}</p>
        </StateField>
      )}
      
      {context.objectives !== undefined && context.objectives.length > 0 && (
        <StateField label="Objectives">
          <ul className="list-disc list-inside text-secondary mt-1">
            {context.objectives.map((obj) => (
              <li key={obj}>{obj}</li>
            ))}
          </ul>
        </StateField>
      )}
      
      {context.targetUsers !== undefined && context.targetUsers !== "" && (
        <StateField label="Target Users">
          <p className="text-secondary mt-1">{context.targetUsers}</p>
        </StateField>
      )}
      
      {context.scenarioType !== undefined && context.scenarioType !== "" && (
        <StateField label="Scenario">
          <p className="text-secondary mt-1">{context.scenarioType}</p>
        </StateField>
      )}
    </StateSection>
  );
}

