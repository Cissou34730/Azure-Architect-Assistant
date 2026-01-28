import type { ClarificationQuestion } from "../../../types/api";

interface ClarificationQuestionsProps {
  readonly questions: readonly ClarificationQuestion[];
}

export function ClarificationQuestions({
  questions,
}: ClarificationQuestionsProps) {
  if (questions.length === 0) {
    return (
      <p className="text-gray-600">
        No open questions found.
      </p>
    );
  }

  const sortedQuestions = [...questions].sort(
    (a, b) => (a.priority ?? 999) - (b.priority ?? 999)
  );

  return (
    <ul className="space-y-2">
      {sortedQuestions.map((q, idx) => {
        const questionText = q.question ?? "Unnamed question";
        const priority = q.priority !== undefined ? `P${String(q.priority)}` : "P-";
        const status = q.status ?? "open";

        return (
          <li
            key={q.id !== "" ? q.id : `q-${String(idx)}`}
            className="bg-white p-3 rounded-md border border-gray-200"
          >
            <div className="flex items-start justify-between gap-3">
              <p className="text-gray-900">{questionText}</p>
              <span className="text-xs text-gray-600">
                {priority} • {status}
              </span>
            </div>
          </li>
        );
      })}
    </ul>
  );
}
