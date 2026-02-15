import { HelpCircle } from "lucide-react";
import { Virtuoso } from "react-virtuoso";
import type { ClarificationQuestion as Question } from "../../../../../types/api";

interface QuestionsTabProps {
  readonly questions: readonly Question[];
}

export function QuestionsTab({ questions }: QuestionsTabProps) {
  if (questions.length === 0) {
    return (
      <div className="p-4 text-center text-sm text-dim">
        No clarification questions at the moment.
      </div>
    );
  }

  const getPriorityColor = (priority: number): string => {
    switch (priority) {
      case 1: return "bg-danger-soft text-danger-strong";
      case 2: return "bg-warning-soft text-warning";
      case 3: return "bg-brand-soft text-brand-strong";
      default: return "bg-muted text-secondary";
    }
  };

  return (
    <div className="h-full">
      <Virtuoso
        data={questions}
        className="panel-scroll"
        itemContent={(_index, question) => (
          <div className="px-4 py-1">
            <div
              className="p-3 bg-card rounded-lg border border-border"
            >
              <div className="flex items-start gap-2">
                <HelpCircle className="h-4 w-4 text-brand shrink-0 mt-0.5" />
                <div className="flex-1">
                  <div className="text-sm text-secondary mb-2">{question.question}</div>
                  <div className="flex items-center gap-2">
                    {question.priority !== undefined && (
                      <span
                        className={`text-xs px-2 py-0.5 rounded-full ${getPriorityColor(question.priority)}`}
                      >
                        P{question.priority}
                      </span>
                    )}
                    {question.status !== "" && (
                      <span className="text-xs text-dim">{question.status}</span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
        style={{ height: "100%" }}
      />
    </div>
  );
}



