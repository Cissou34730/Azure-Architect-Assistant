import { Search } from "lucide-react";

export type ViewMode = "grid" | "table";
export type StatusFilter =
  | "all"
  | "draft"
  | "accepted"
  | "deprecated"
  | "superseded";

interface AdrFiltersProps {
  readonly statusFilter: StatusFilter;
  readonly onStatusFilterChange: (status: StatusFilter) => void;
  readonly searchQuery: string;
  readonly onSearchQueryChange: (query: string) => void;
  readonly viewMode: ViewMode;
  readonly onViewModeChange: (mode: ViewMode) => void;
}

export function AdrFilters({
  statusFilter,
  onStatusFilterChange,
  searchQuery,
  onSearchQueryChange,
  viewMode,
  onViewModeChange,
}: AdrFiltersProps) {
  const statuses: readonly StatusFilter[] = [
    "all",
    "draft",
    "accepted",
    "deprecated",
  ];

  return (
    <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
      <div className="flex gap-2 flex-wrap">
        {statuses.map((status) => (
          <button
            key={status}
            type="button"
            onClick={() => {
              onStatusFilterChange(status);
            }}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors capitalize ${
              statusFilter === status
                ? "bg-brand text-inverse"
                : "bg-muted text-secondary hover:bg-border"
            }`}
          >
            {status}
          </button>
        ))}
      </div>

      <div className="flex gap-2 w-full sm:w-auto">
        <div className="relative flex-1 sm:w-64">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-dim" />
          <input
            type="text"
            value={searchQuery}
            onChange={(event) => {
              onSearchQueryChange(event.target.value);
            }}
            placeholder="Search ADRs..."
            className="w-full pl-10 pr-4 py-2 border border-border-stronger rounded-lg focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent text-sm"
          />
        </div>

        <div className="flex border border-border-stronger rounded-lg overflow-hidden">
          <button
            type="button"
            onClick={() => {
              onViewModeChange("grid");
            }}
            className={`px-3 py-2 text-sm ${
              viewMode === "grid" ? "bg-muted" : "hover:bg-surface"
            }`}
          >
            Grid
          </button>
          <button
            type="button"
            onClick={() => {
              onViewModeChange("table");
            }}
            className={`px-3 py-2 text-sm border-l border-border-stronger ${
              viewMode === "table" ? "bg-muted" : "hover:bg-surface"
            }`}
          >
            Table
          </button>
        </div>
      </div>
    </div>
  );
}


