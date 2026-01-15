import { ProjectState } from "../../../../types/api";
import { Section } from "./StateShared";
import { renderMaybeNamed } from "./utils";

interface ContextSectionProps {
  readonly context: ProjectState["context"];
}

export function ContextSection({ context }: ContextSectionProps) {
  return (
    <Section title="Context">
      <p>
        <strong>Summary:</strong> {context.summary}
      </p>
      <p>
        <strong>Target Users:</strong> {context.targetUsers}
      </p>
      <p>
        <strong>Scenario Type:</strong> {context.scenarioType}
      </p>
      <p>
        <strong>Objectives:</strong>
      </p>
      <ul className="list-disc list-inside">
        {context.objectives.map((obj, i) => (
          // eslint-disable-next-line react/no-array-index-key
          <li key={i}>{renderMaybeNamed(obj)}</li>
        ))}
      </ul>
    </Section>
  );
}
