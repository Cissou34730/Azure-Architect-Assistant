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
    <div className="p-4 border-b border-gray-100 bg-white sticky top-0 z-10">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className="p-1.5 bg-blue-50 rounded-lg">
            <FileBox className="h-4 w-4 text-blue-600" />
          </div>
          <h2 className="text-sm font-semibold text-gray-900 tracking-tight">Project Hub</h2>
        </div>
        <button
          onClick={onToggle}
          className="p-1 hover:bg-gray-100 rounded transition-colors"
          type="button"
        >
          <ChevronRight className="h-5 w-5 text-gray-600" />
        </button>
      </div>

      <ProjectStats 
        adrCount={adrCount}
        findingCount={findingCount}
        requirementCount={requirementCount}
      />

      <div className="relative mt-4">
        <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-gray-400" />
        <input
          type="text"
          placeholder="Search artifacts..."
          className="w-full pl-8 pr-3 py-1.5 text-xs bg-gray-50 border border-gray-200 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 transition-all"
          value={searchQuery}
          onChange={(event) => { onSearchChange(event.target.value); }}
        />
      </div>
    </div>
  );
}
