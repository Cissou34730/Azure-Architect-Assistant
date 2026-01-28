import { ChevronRight } from "lucide-react";
import { Badge } from "../../../../../components/common";

interface SectionProps {
  readonly title: string;
  readonly expanded: boolean;
  readonly onToggle: () => void;
  readonly count?: number;
  readonly onViewAll?: () => void;
  readonly children: React.ReactNode;
}

export function Section({ title, expanded, onToggle, count, onViewAll, children }: SectionProps) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      <div className="flex items-center justify-between px-3 py-2 border-b border-gray-100">
        <button
          onClick={onToggle}
          className="flex items-center gap-2 flex-1 text-left hover:text-blue-600 transition-colors"
        >
          <ChevronRight
            className={`h-4 w-4 transition-transform ${expanded ? "rotate-90" : ""}`}
          />
          <span className="text-sm font-medium text-gray-700">{title}</span>
          {count !== undefined && count > 0 && (
            <Badge size="sm">
              {count}
            </Badge>
          )}
        </button>
        {onViewAll !== undefined && count !== undefined && count > 0 && (
          <button
            onClick={onViewAll}
            className="text-xs text-blue-600 hover:text-blue-700 px-2"
          >
            View all
          </button>
        )}
      </div>
      {expanded && <div className="p-3">{children}</div>}
    </div>
  );
}
