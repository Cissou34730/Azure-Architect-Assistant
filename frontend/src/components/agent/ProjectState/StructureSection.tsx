import { ProjectState } from "../../../types/agent";
import { StateSection, StateField } from "./StateShared";

interface StructureSectionProps {
  readonly structure: NonNullable<ProjectState["applicationStructure"]>;
}

export function StructureSection({ structure }: StructureSectionProps) {
  return (
    <StateSection icon="🏗️" title="Application Structure">
      {structure.components !== undefined && structure.components.length > 0 && (
        <StateField label="Components">
          <ul className="space-y-1 mt-1">
            {structure.components.map((comp) => (
              <li key={comp.name} className="text-secondary">
                <span className="font-medium">{comp.name}:</span> {comp.description}
              </li>
            ))}
          </ul>
        </StateField>
      )}
      
      {structure.integrations !== undefined && structure.integrations.length > 0 && (
        <StateField label="Integrations">
          <p className="text-secondary mt-1">
            {structure.integrations.join(", ")}
          </p>
        </StateField>
      )}
    </StateSection>
  );
}

