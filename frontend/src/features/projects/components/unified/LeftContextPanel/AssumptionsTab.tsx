import { Lightbulb } from "lucide-react";
import { Virtuoso } from "react-virtuoso";

interface Assumption {
  readonly id?: string;
  readonly text?: string;
}

interface AssumptionsTabProps {
  readonly assumptions: readonly Assumption[];
}

export function AssumptionsTab({ assumptions }: AssumptionsTabProps) {
  if (assumptions.length === 0) {
    return (
      <div className="p-4 text-center text-sm text-gray-500">
        No assumptions documented yet.
      </div>
    );
  }

  return (
    <div className="h-full">
      <Virtuoso
        data={assumptions}
        className="panel-scroll"
        itemContent={(index, assumption) => (
          <div className="px-4 py-1">
            <div
              key={assumption.id ?? `a-${index}`}
              className="flex items-start gap-2 p-3 bg-white rounded-lg border border-gray-200"
            >
              <Lightbulb className="h-4 w-4 text-amber-600 shrink-0 mt-0.5" />
              <div className="text-sm text-gray-700">{assumption.text ?? ""}</div>
            </div>
          </div>
        )}
        style={{ height: "100%" }}
      />
    </div>
  );
}
