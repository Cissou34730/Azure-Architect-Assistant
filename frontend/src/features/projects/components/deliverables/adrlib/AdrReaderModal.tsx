import { Badge } from "../../../../../components/common";
import { X, ExternalLink } from "lucide-react";
import type { AdrArtifact } from "../../../../../types/api";

interface AdrSectionProps {
  readonly title: string;
  readonly content: string | undefined;
}

function AdrSection({ title, content }: AdrSectionProps) {
  if (content === undefined || content === "") return null;

  return (
    <section>
      <h3 className="text-sm font-semibold text-gray-700 mb-2">{title}</h3>
      <p className="text-sm text-gray-900 whitespace-pre-wrap">{content}</p>
    </section>
  );
}

interface AdrRelatedListProps {
  readonly title: string;
  readonly ids: readonly string[] | undefined;
  readonly badgeVariant: "default" | "info";
}

function AdrRelatedList({ title, ids, badgeVariant }: AdrRelatedListProps) {
  if (ids === undefined || ids.length === 0) return null;

  return (
    <div>
      <h4 className="text-xs font-semibold text-gray-700 mb-2">{title}</h4>
      <div className="space-y-1">
        {ids.map((id) => (
          <Badge key={id} variant={badgeVariant} size="sm">
            {id}
          </Badge>
        ))}
      </div>
    </div>
  );
}

interface AdrCitationsProps {
  readonly citations:
    | readonly { url?: string; kind?: string; title?: string }[]
    | undefined;
}

function AdrCitations({ citations }: AdrCitationsProps) {
  if (citations === undefined || citations.length === 0) return null;

  return (
    <div>
      <h4 className="text-xs font-semibold text-gray-700 mb-2">Citations</h4>
      <div className="space-y-2">
        {citations.map((citation, index) => (
          <div
            key={citation.url !== undefined && citation.url !== "" ? `${citation.url}-${index}` : `citation-${index}`}
            className="text-xs"
          >
            {citation.url !== undefined && citation.url !== "" ? (
              <a
                href={citation.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 hover:text-blue-700 flex items-center gap-1"
              >
                <span>{citation.kind ?? "Source"}</span>
                <ExternalLink className="h-3 w-3" />
              </a>
            ) : (
              <span className="text-gray-600">{citation.kind ?? "Source"}</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

interface AdrReaderModalProps {
  readonly adr: AdrArtifact;
  readonly onClose: () => void;
}

export function AdrReaderModal({ adr, onClose }: AdrReaderModalProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-75 p-4 overflow-y-auto">
      <div className="bg-white rounded-lg max-w-4xl w-full my-8">
        <div className="px-6 py-4 border-b border-gray-200 flex items-start justify-between sticky top-0 bg-white rounded-t-lg">
          <div className="flex-1">
            <div className="flex items-start gap-3 mb-2">
              <h2 className="text-xl font-semibold text-gray-900 flex-1">
                {adr.title}
              </h2>
              <Badge
                variant={adr.status === "accepted" ? "success" : "warning"}
                size="md"
              >
                {adr.status}
              </Badge>
            </div>
            {adr.createdAt !== undefined && (
              <p className="text-sm text-gray-600">
                Created: {new Date(adr.createdAt).toLocaleDateString()}
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="ml-4 p-2 hover:bg-gray-100 rounded-lg transition-colors"
            aria-label="Close"
          >
            <X className="h-5 w-5 text-gray-600" />
          </button>
        </div>

        <div className="px-6 py-6 space-y-6">
          <AdrSection title="Context" content={adr.context} />
          <AdrSection title="Decision" content={adr.decision} />
          <AdrSection title="Consequences" content={adr.consequences} />

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-4 border-t border-gray-200">
            <AdrRelatedList
              title="Related Requirements"
              ids={adr.relatedRequirementIds}
              badgeVariant="default"
            />
            <AdrRelatedList
              title="Related Diagrams"
              ids={adr.relatedDiagramIds}
              badgeVariant="info"
            />
            <AdrCitations citations={adr.sourceCitations} />
          </div>
        </div>
      </div>
    </div>
  );
}
