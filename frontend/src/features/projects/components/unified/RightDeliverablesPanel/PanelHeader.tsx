import { FileBox, ChevronRight, Search } from "lucide-react";
import { ProjectStats } from "./ProjectStats";

interface PanelHeaderProps {
  readonly onToggle: () => void;
  readonly adrCount: number;
  readonly findingCount: number;
  readonly requirementCount: number;
  readonly searchQuery: string;
  readonly onSearchChange: (value: string) => void;
}

export function PanelHeader({
  onToggle,
  adrCount,
  findingCount,
  requirementCount,
  searchQuery,
  onSearchChange,
}: PanelHeaderProps) {
  return (
    <div className="p-4 border-b border-border bg-card sticky top-0 z-10">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className="p-1.5 bg-brand-soft rounded-lg">
            <FileBox className="h-4 w-4 text-brand" />
          </div>
          <h2 className="text-sm font-semibold text-foreground tracking-tight">Project Hub</h2>
        </div>
        <button
          onClick={onToggle}
          className="p-1 hover:bg-muted rounded transition-colors"
          type="button"
        >
          <ChevronRight className="h-5 w-5 text-secondary" />
        </button>
      </div>

      <ProjectStats 
        adrCount={adrCount}
        findingCount={findingCount}
        requirementCount={requirementCount}
      />

      <div className="relative mt-4">
        <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-dim" />
        <input
          type="text"
          placeholder="Search artifacts..."
          className="w-full pl-8 pr-3 py-1.5 text-xs bg-surface border border-border rounded-md focus:outline-none focus:ring-1 focus:ring-brand focus:border-brand transition-all"
          value={searchQuery}
          onChange={(event) => { onSearchChange(event.target.value); }}
        />
      </div>
    </div>
  );
}


