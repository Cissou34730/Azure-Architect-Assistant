import { HelpCircle } from "lucide-react";
import type { ClarificationQuestion as Question } from "../../../../../types/api";

interface QuestionsTabProps {
  readonly questions: readonly Question[];
}

export function QuestionsTab({ questions }: QuestionsTabProps) {
  if (questions.length === 0) {
    return (
      <div className="p-4 text-center text-sm text-gray-500">
        No clarification questions at the moment.
      </div>
    );
  }

  const getPriorityColor = (priority: number): string => {
    switch (priority) {
      case 1: return "bg-red-100 text-red-700";
      case 2: return "bg-amber-100 text-amber-700";
      case 3: return "bg-blue-100 text-blue-700";
      default: return "bg-gray-100 text-gray-700";
    }
  };

  return (
    <div className="p-4 space-y-2">
      {questions.map((question, idx) => (
        <div
          key={question.id ?? `q-${idx}`}
          className="p-3 bg-white rounded-lg border border-gray-200"
        >
          <div className="flex items-start gap-2">
            <HelpCircle className="h-4 w-4 text-blue-600 shrink-0 mt-0.5" />
            <div className="flex-1">
              <div className="text-sm text-gray-700 mb-2">{question.question}</div>
              <div className="flex items-center gap-2">
                {question.priority !== undefined && (
                  <span
                    className={`text-xs px-2 py-0.5 rounded-full ${getPriorityColor(question.priority)}`}
                  >
                    P{question.priority}
                  </span>
                )}
                {question.status !== "" && (
                  <span className="text-xs text-gray-500">{question.status}</span>
                )}
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
