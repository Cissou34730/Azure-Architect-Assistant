import type { FindingArtifact, SourceCitation } from "../../../types/api";

interface FindingListProps {
  readonly findings: readonly FindingArtifact[];
}

function SeverityBadge({ severity }: { readonly severity: string }) {
  if (severity === "") return null;

  const colors: Record<string, string> = {
    low: "bg-blue-100 text-blue-800",
    medium: "bg-yellow-100 text-yellow-800",
    high: "bg-orange-100 text-orange-800",
    critical: "bg-red-100 text-red-800",
  };
  const colorClass = colors[severity.toLowerCase()] ?? "bg-gray-100 text-gray-800";
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium ${colorClass}`}>
      {severity}
    </span>
  );
}

function CitationList({ citations }: { readonly citations: readonly SourceCitation[] }) {
  if (citations.length === 0) return null;

  return (
    <div className="mt-3 text-xs text-gray-600">
      <p className="font-medium">Citations</p>
      <ul className="list-disc list-inside">
        {citations.map((citation, idx) => {
          const kind = citation.kind ?? "source";
          const url = (citation.url ?? "").trim();
          const note = (citation.note ?? "").trim();
          return (
            <li key={`cit-${String(idx)}`}>
              {kind}
              {url !== "" ? ` — ${url}` : ""}
              {note !== "" ? ` (${note})` : ""}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function FindingHeader({ title, id, severity, wafPillar, wafTopic }: { readonly title: string; readonly id: string; readonly severity: string; readonly wafPillar?: string; readonly wafTopic?: string }) {
  return (
    <div className="flex items-start justify-between gap-3">
      <div>
        <h4 className="font-semibold text-gray-900">{title}</h4>
        <div className="flex flex-wrap gap-2 mt-1">
          <SeverityBadge severity={severity} />
          {(wafPillar !== undefined || (wafTopic !== undefined && wafTopic !== "")) && (
            <span className="text-xs text-gray-600">
              {wafPillar}
              {wafTopic !== undefined && wafTopic !== "" ? ` — ${wafTopic}` : ""}
            </span>
          )}
        </div>
      </div>
      {id !== "" && <span className="text-xs text-gray-500">{id}</span>}
    </div>
  );
}

function FindingContent({ description, remediation }: { readonly description: string; readonly remediation: string }) {
  return (
    <>
      {description !== "" && (
        <div className="mt-3">
          <p className="text-xs font-medium text-gray-700">Description</p>
          <p className="text-sm text-gray-700 whitespace-pre-wrap">{description}</p>
        </div>
      )}

      {remediation !== "" && (
        <div className="mt-3">
          <p className="text-xs font-medium text-gray-700">Remediation</p>
          <p className="text-sm text-gray-700 whitespace-pre-wrap">{remediation}</p>
        </div>
      )}
    </>
  );
}

function FindingItem({ finding }: { readonly finding: FindingArtifact }) {
  const title = finding.title !== "" ? finding.title : "Untitled finding";
  const reqIds = finding.relatedRequirementIds;
  const citations = finding.sourceCitations;

  return (
    <div className="bg-white p-4 rounded-md border border-gray-200">
      <FindingHeader
        title={title}
        id={finding.id}
        severity={finding.severity}
        wafPillar={finding.wafPillar}
        wafTopic={finding.wafTopic}
      />

      {finding.createdAt !== undefined && finding.createdAt !== "" && (
        <p className="text-xs text-gray-500 mt-1">{finding.createdAt}</p>
      )}

      <FindingContent description={finding.description} remediation={finding.remediation} />

      {reqIds.length > 0 && (
        <div className="mt-3 text-xs text-gray-600">
          <p className="font-medium">Linked requirements</p>
          <ul className="list-disc list-inside">
            {reqIds.map((id) => (
              <li key={`req-${id}`}>{id}</li>
            ))}
          </ul>
        </div>
      )}

      <CitationList citations={citations} />
    </div>
  );
}

export function FindingList({ findings }: FindingListProps) {
  if (findings.length === 0) {
    return <p className="text-gray-600">No findings yet. Run validation via Agent chat.</p>;
  }

  const sortedFindings = [...findings].sort((a, b) =>
    (a.createdAt ?? "").localeCompare(b.createdAt ?? "")
  );

  return (
    <div className="space-y-3">
      {sortedFindings.map((finding, idx) => (
        <FindingItem key={finding.id !== "" ? finding.id : `fi-${idx}`} finding={finding} />
      ))}
    </div>
  );
}
