import { useState } from "react";
import { FileText, Search, X, ExternalLink } from "lucide-react";
import { Card, CardContent, Badge, EmptyState } from "../../../../components/common";
import type { AdrArtifact } from "../../../../types/api";

interface AdrLibraryProps {
  adrs: readonly AdrArtifact[];
}

type ViewMode = "grid" | "table";
type StatusFilter = "all" | "draft" | "accepted" | "deprecated" | "superseded";

export function AdrLibrary({ adrs }: AdrLibraryProps) {
  const [viewMode, setViewMode] = useState<ViewMode>("grid");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedAdr, setSelectedAdr] = useState<AdrArtifact | null>(null);

  const filteredAdrs = adrs.filter((adr) => {
    // Status filter
    if (statusFilter !== "all") {
      const status = (adr.status || "").toLowerCase();
      if (status !== statusFilter) return false;
    }

    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      const title = (adr.title || "").toLowerCase();
      const context = (adr.context || "").toLowerCase();
      const decision = (adr.decision || "").toLowerCase();
      return title.includes(query) || context.includes(query) || decision.includes(query);
    }

    return true;
  });

  if (adrs.length === 0) {
    return (
      <EmptyState
        icon={FileText}
        title="No ADRs yet"
        description="Create Architecture Decision Records using the Workspace chat"
        action={
          <button className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors text-sm">
            Go to Workspace
          </button>
        }
      />
    );
  }

  const getStatusVariant = (status: string): "success" | "warning" | "default" | "error" => {
    const s = status.toLowerCase();
    if (s === "accepted") return "success";
    if (s === "draft") return "warning";
    if (s === "deprecated" || s === "superseded") return "error";
    return "default";
  };

  return (
    <div className="space-y-6">
      {/* Filters and Search */}
      <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
        <div className="flex gap-2 flex-wrap">
          {(["all", "draft", "accepted", "deprecated"] as StatusFilter[]).map((status) => (
            <button
              key={status}
              onClick={() => setStatusFilter(status)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors capitalize ${
                statusFilter === status
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 text-gray-700 hover:bg-gray-200"
              }`}
            >
              {status}
            </button>
          ))}
        </div>

        <div className="flex gap-2 w-full sm:w-auto">
          <div className="relative flex-1 sm:w-64">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search ADRs..."
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
            />
          </div>

          <div className="flex border border-gray-300 rounded-lg overflow-hidden">
            <button
              onClick={() => setViewMode("grid")}
              className={`px-3 py-2 text-sm ${
                viewMode === "grid" ? "bg-gray-100" : "hover:bg-gray-50"
              }`}
            >
              Grid
            </button>
            <button
              onClick={() => setViewMode("table")}
              className={`px-3 py-2 text-sm border-l border-gray-300 ${
                viewMode === "table" ? "bg-gray-100" : "hover:bg-gray-50"
              }`}
            >
              Table
            </button>
          </div>
        </div>
      </div>

      {/* Results Count */}
      <p className="text-sm text-gray-600">
        {filteredAdrs.length} of {adrs.length} ADRs
      </p>

      {/* Content */}
      {filteredAdrs.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          No ADRs match your filters
        </div>
      ) : viewMode === "grid" ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredAdrs.map((adr) => (
            <Card
              key={adr.id || adr.title}
              hover
              onClick={() => setSelectedAdr(adr)}
            >
              <CardContent className="p-4">
                <div className="flex items-start justify-between gap-2 mb-2">
                  <h3 className="font-medium text-gray-900 text-sm line-clamp-2 flex-1">
                    {adr.title || "Untitled ADR"}
                  </h3>
                  <Badge variant={getStatusVariant(adr.status || "")} size="sm">
                    {adr.status || "draft"}
                  </Badge>
                </div>

                {adr.context && (
                  <p className="text-xs text-gray-600 line-clamp-3 mb-3">
                    {adr.context}
                  </p>
                )}

                <div className="flex items-center gap-2 text-xs text-gray-500">
                  {adr.createdAt && (
                    <span>{new Date(adr.createdAt).toLocaleDateString()}</span>
                  )}
                  {adr.relatedRequirementIds && adr.relatedRequirementIds.length > 0 && (
                    <>
                      <span>•</span>
                      <span>{adr.relatedRequirementIds.length} requirements</span>
                    </>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200">
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-600 uppercase">
                  Title
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-600 uppercase">
                  Status
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-600 uppercase">
                  Created
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-600 uppercase">
                  Related
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {filteredAdrs.map((adr) => (
                <tr
                  key={adr.id || adr.title}
                  onClick={() => setSelectedAdr(adr)}
                  className="hover:bg-gray-50 cursor-pointer"
                >
                  <td className="px-4 py-3 text-sm text-gray-900">
                    {adr.title || "Untitled ADR"}
                  </td>
                  <td className="px-4 py-3">
                    <Badge variant={getStatusVariant(adr.status || "")} size="sm">
                      {adr.status || "draft"}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600">
                    {adr.createdAt
                      ? new Date(adr.createdAt).toLocaleDateString()
                      : "—"}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600">
                    {(adr.relatedRequirementIds?.length || 0) +
                      (adr.relatedDiagramIds?.length || 0)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Reader Modal */}
      {selectedAdr && (
        <AdrReaderModal adr={selectedAdr} onClose={() => setSelectedAdr(null)} />
      )}
    </div>
  );
}

function AdrReaderModal({ adr, onClose }: { adr: AdrArtifact; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-75 p-4 overflow-y-auto">
      <div className="bg-white rounded-lg max-w-4xl w-full my-8">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 flex items-start justify-between sticky top-0 bg-white rounded-t-lg">
          <div className="flex-1">
            <div className="flex items-start gap-3 mb-2">
              <h2 className="text-xl font-semibold text-gray-900 flex-1">
                {adr.title || "Untitled ADR"}
              </h2>
              <Badge variant={adr.status === "accepted" ? "success" : "warning"} size="md">
                {adr.status || "draft"}
              </Badge>
            </div>
            {adr.createdAt && (
              <p className="text-sm text-gray-600">
                Created: {new Date(adr.createdAt).toLocaleDateString()}
              </p>
            )}
          </div>
          <button
            onClick={onClose}
            className="ml-4 p-2 hover:bg-gray-100 rounded-lg transition-colors"
            aria-label="Close"
          >
            <X className="h-5 w-5 text-gray-600" />
          </button>
        </div>

        {/* Content */}
        <div className="px-6 py-6 space-y-6">
          {adr.context && (
            <section>
              <h3 className="text-sm font-semibold text-gray-700 mb-2">Context</h3>
              <p className="text-sm text-gray-900 whitespace-pre-wrap">{adr.context}</p>
            </section>
          )}

          {adr.decision && (
            <section>
              <h3 className="text-sm font-semibold text-gray-700 mb-2">Decision</h3>
              <p className="text-sm text-gray-900 whitespace-pre-wrap">{adr.decision}</p>
            </section>
          )}

          {adr.consequences && (
            <section>
              <h3 className="text-sm font-semibold text-gray-700 mb-2">Consequences</h3>
              <p className="text-sm text-gray-900 whitespace-pre-wrap">{adr.consequences}</p>
            </section>
          )}

          {/* Related Items */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-4 border-t border-gray-200">
            {adr.relatedRequirementIds && adr.relatedRequirementIds.length > 0 && (
              <div>
                <h4 className="text-xs font-semibold text-gray-700 mb-2">
                  Related Requirements
                </h4>
                <div className="space-y-1">
                  {adr.relatedRequirementIds.map((id) => (
                    <Badge key={id} variant="default" size="sm">
                      {id}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {adr.relatedDiagramIds && adr.relatedDiagramIds.length > 0 && (
              <div>
                <h4 className="text-xs font-semibold text-gray-700 mb-2">
                  Related Diagrams
                </h4>
                <div className="space-y-1">
                  {adr.relatedDiagramIds.map((id) => (
                    <Badge key={id} variant="info" size="sm">
                      {id}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {adr.sourceCitations && adr.sourceCitations.length > 0 && (
              <div>
                <h4 className="text-xs font-semibold text-gray-700 mb-2">Citations</h4>
                <div className="space-y-2">
                  {adr.sourceCitations.map((citation, idx) => (
                    <div key={idx} className="text-xs">
                      {citation.url ? (
                        <a
                          href={citation.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-600 hover:text-blue-700 flex items-center gap-1"
                        >
                          <span>{citation.kind || "Source"}</span>
                          <ExternalLink className="h-3 w-3" />
                        </a>
                      ) : (
                        <span className="text-gray-600">{citation.kind || "Source"}</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
