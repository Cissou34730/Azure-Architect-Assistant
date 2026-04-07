import { StateSection } from "./StateShared";

interface OpenQuestionsSectionProps {
  readonly questions: readonly string[];
}

export function OpenQuestionsSection({ questions }: OpenQuestionsSectionProps) {
  if (questions.length === 0) {
    return null;
  }

  return (
    <StateSection icon="❓" title="Open Questions">
      <div className="bg-warning-soft rounded-lg p-3">
        <ul className="list-disc list-inside text-sm text-secondary space-y-1">
          {questions.map((q) => (
            <li key={q.substring(0, 30)}>{q}</li>
          ))}
        </ul>
      </div>
    </StateSection>
  );
}


