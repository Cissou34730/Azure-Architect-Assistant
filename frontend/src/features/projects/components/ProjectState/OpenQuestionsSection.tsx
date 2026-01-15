import { ProjectState } from "../../../../types/api";
import { Section } from "./StateShared";
import { renderMaybeNamed } from "./utils";

interface OpenQuestionsSectionProps {
  readonly questions: ProjectState["openQuestions"];
}

export function OpenQuestionsSection({
  questions,
}: OpenQuestionsSectionProps) {
  if (questions.length === 0) return null;

  return (
    <Section title="Open Questions">
      <ul className="list-disc list-inside">
        {questions.map((q, i) => (
          // eslint-disable-next-line react/no-array-index-key
          <li key={i}>{renderMaybeNamed(q)}</li>
        ))}
      </ul>
    </Section>
  );
}
