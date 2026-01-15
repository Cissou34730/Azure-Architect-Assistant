import { ProjectState } from "../../../../types/api";
import { Section } from "./StateShared";

interface NfrSectionProps {
  readonly nfrs: ProjectState["nfrs"];
}

export function NfrSection({ nfrs }: NfrSectionProps) {
  if (nfrs === undefined) return null;

  return (
    <Section title="Non-Functional Requirements">
      <p>
        <strong>Availability:</strong> {nfrs.availability}
      </p>
      <p>
        <strong>Security:</strong> {nfrs.security}
      </p>
      <p>
        <strong>Performance:</strong> {nfrs.performance}
      </p>
      <p>
        <strong>Cost:</strong> {nfrs.costConstraints}
      </p>
    </Section>
  );
}
