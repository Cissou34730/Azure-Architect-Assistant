import type { TraceabilityLink, TraceabilityIssue } from "../../../types/api";

interface TraceabilityPanelProps {
  readonly traceabilityGroups: readonly {
    readonly key: string;
    readonly links: readonly TraceabilityLink[];
  }[];
  readonly traceabilityIssues: readonly TraceabilityIssue[];
}

export function TraceabilityPanel({
  traceabilityGroups,
  traceabilityIssues,
}: TraceabilityPanelProps) {
  if (traceabilityGroups.length === 0) {
    return (
      <p className="text-gray-600">No traceability links yet.</p>
    );
  }

  return (
    <div className="space-y-6">
      <div className="space-y-3">
        {traceabilityGroups.map((group) => (
          <div
            key={group.key}
            className="bg-white p-4 rounded-md border border-gray-200"
          >
            <h4 className="font-semibold text-gray-900">{group.key}</h4>
            <ul className="mt-2 space-y-1 text-xs text-gray-700">
              {group.links.map((link, idx: number) => (
                <li
                  key={`${group.key}-${link.id !== "" ? link.id : String(idx)}`}
                  className="flex items-start justify-between gap-3"
                >
                  <span>
                    → {link.toType !== "" ? link.toType : "unknown"}:
                    {link.toId !== "" ? link.toId : "unknown"}
                  </span>
                  {link.id !== "" && (
                    <span className="text-gray-500">{link.id}</span>
                  )}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      {traceabilityIssues.length > 0 && (
        <div className="mt-3 text-xs text-gray-600">
          <p className="font-medium">Issues</p>
          <ul className="list-disc list-inside">
            {traceabilityIssues.map((issue, idx: number) => (
              <li key={`issue-${issue.id !== "" ? issue.id : String(idx)}`}>
                {issue.kind !== "" ? issue.kind : "issue"}:{" "}
                {issue.message !== "" ? issue.message : "unknown"}
                {issue.linkId !== undefined && issue.linkId !== ""
                  ? ` (link: ${issue.linkId})`
                  : ""}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
