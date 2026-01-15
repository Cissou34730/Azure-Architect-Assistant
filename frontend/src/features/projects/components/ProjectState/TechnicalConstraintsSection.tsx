import { ProjectState } from "../../../../types/api";
import { Section } from "./StateShared";
import { renderMaybeNamed } from "./utils";

interface TechnicalConstraintsSectionProps {
  readonly constraints: ProjectState["technicalConstraints"];
}

export function TechnicalConstraintsSection({
  constraints,
}: TechnicalConstraintsSectionProps) {
  return (
    <Section title="Technical Constraints">
      <p>
        <strong>Constraints:</strong>
      </p>
      <ul className="list-disc list-inside">
        {constraints.constraints.map((c, i) => (
          // eslint-disable-next-line react/no-array-index-key
          <li key={i}>{renderMaybeNamed(c)}</li>
        ))}
      </ul>
      <p>
        <strong>Assumptions:</strong>
      </p>
      <ul className="list-disc list-inside">
        {constraints.assumptions.map((a, i) => (
          // eslint-disable-next-line react/no-array-index-key
          <li key={i}>{renderMaybeNamed(a)}</li>
        ))}
      </ul>
    </Section>
  );
}
