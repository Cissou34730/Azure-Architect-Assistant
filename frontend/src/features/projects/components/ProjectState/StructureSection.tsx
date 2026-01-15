import { ProjectState } from "../../../../types/api";
import { Section } from "./StateShared";
import { renderMaybeNamed } from "./utils";

interface StructureSectionProps {
  readonly structure: ProjectState["applicationStructure"];
}

export function StructureSection({ structure }: StructureSectionProps) {
  if (structure === undefined) return null;

  return (
    <Section title="Application Structure">
      <p>
        <strong>Components:</strong>
      </p>
      <ul className="list-disc list-inside">
        {structure.components.map((comp, i) => (
          // eslint-disable-next-line react/no-array-index-key
          <li key={i}>{renderMaybeNamed(comp)}</li>
        ))}
      </ul>
      <p>
        <strong>Integrations:</strong>
      </p>
      <ul className="list-disc list-inside">
        {structure.integrations.map((intg, i) => (
          // eslint-disable-next-line react/no-array-index-key
          <li key={i}>{renderMaybeNamed(intg)}</li>
        ))}
      </ul>
    </Section>
  );
}
