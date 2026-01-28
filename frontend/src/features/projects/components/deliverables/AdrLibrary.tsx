import { useState, useMemo } from "react";
import { FileText } from "lucide-react";
import { EmptyState } from "../../../../components/common";
import type { AdrArtifact } from "../../../../types/api";
import { AdrFilters, type ViewMode, type StatusFilter } from "./adrlib/AdrFilters";
import { AdrGrid } from "./adrlib/AdrGrid";
import { AdrTable } from "./adrlib/AdrTable";
import { AdrReaderModal } from "./adrlib/AdrReaderModal";

export interface AdrLibraryProps {
  readonly adrs: readonly AdrArtifact[];
}

export function AdrLibrary({ adrs }: AdrLibraryProps) {
  const [viewMode, setViewMode] = useState<ViewMode>("grid");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedAdr, setSelectedAdr] = useState<AdrArtifact | null>(null);

  const filteredAdrs = useMemo(() => {
    return adrs.filter((adr) => {
      // Status filter
      if (statusFilter !== "all") {
        const adrStatus = adr.status.toLowerCase();
        if (adrStatus !== statusFilter) return false;
      }

      // Search filter
      if (searchQuery !== "") {
        const query = searchQuery.toLowerCase();
        const title = adr.title.toLowerCase();
        const context = adr.context.toLowerCase();
        const decision = adr.decision.toLowerCase();
        return (
          title.includes(query) ||
          context.includes(query) ||
          decision.includes(query)
        );
      }

      return true;
    });
  }, [adrs, statusFilter, searchQuery]);

  if (adrs.length === 0) {
    return (
      <EmptyState
        icon={FileText}
        title="No ADRs yet"
        description="Create Architecture Decision Records using the Workspace chat"
        action={
          <button
            type="button"
            className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors text-sm"
          >
            Go to Workspace
          </button>
        }
      />
    );
  }

  return (
    <div className="space-y-6">
      <AdrFilters
        statusFilter={statusFilter}
        onStatusFilterChange={setStatusFilter}
        searchQuery={searchQuery}
        onSearchQueryChange={setSearchQuery}
        viewMode={viewMode}
        onViewModeChange={setViewMode}
      />

      <p className="text-sm text-gray-600">
        {filteredAdrs.length} of {adrs.length} ADRs
      </p>

      {filteredAdrs.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          No ADRs match your filters
        </div>
      ) : viewMode === "grid" ? (
        <AdrGrid adrs={filteredAdrs} onSelect={setSelectedAdr} />
      ) : (
        <AdrTable adrs={filteredAdrs} onSelect={setSelectedAdr} />
      )}

      {selectedAdr !== null && (
        <AdrReaderModal
          adr={selectedAdr}
          onClose={() => {
            setSelectedAdr(null);
          }}
        />
      )}
    </div>
  );
}

