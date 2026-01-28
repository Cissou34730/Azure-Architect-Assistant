import type { MindMapCoverage } from "../../../types/api";

interface MindMapCoveragePanelProps {
  readonly coverage: MindMapCoverage | undefined;
  readonly topics: readonly {
    readonly key: string;
    readonly status: string;
  }[];
}

export function MindMapCoveragePanel({
  coverage,
  topics,
}: MindMapCoveragePanelProps) {
  if (topics.length === 0) {
    return <p className="text-gray-600">No coverage computed yet.</p>;
  }

  return (
    <div className="space-y-2">
      {coverage?.computedAt !== undefined && coverage.computedAt !== "" && (
        <p className="text-xs text-gray-500">
          Computed at: {coverage.computedAt}
        </p>
      )}
      <ul className="space-y-2">
        {topics.map((topic) => (
          <li
            key={topic.key}
            className="bg-white p-3 rounded-md border border-gray-200 flex items-start justify-between gap-3"
          >
            <span className="text-sm text-gray-900">{topic.key}</span>
            <span className="text-xs text-gray-600">{topic.status}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
