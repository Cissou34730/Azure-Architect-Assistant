import { Card, CardHeader, CardTitle, CardContent, Badge } from "../../../../components/common";
import { CoverageProgress } from "./charts/CoverageProgress";

interface MindMapCoverage {
  readonly version?: string;
  readonly computedAt?: string;
  readonly topics?: Record<string, { readonly status?: string }>;
}

interface ArchitectureCoverageCardProps {
  readonly coverage: MindMapCoverage | null | undefined;
}

interface StatusCounts {
  readonly complete: number;
  readonly partial: number;
  readonly missing: number;
}

function useCoverageData(coverage: MindMapCoverage | null | undefined) {
  const statusCounts = {
    complete: 0,
    partial: 0,
    missing: 0,
  };

  const topics =
    coverage !== null && coverage !== undefined
      ? coverage.topics ?? {}
      : {};
  const topicEntries = Object.entries(topics);

  for (const [, data] of topicEntries) {
    const rawStatus = data.status ?? "missing";
    const status = rawStatus.toLowerCase();
    if (status === "complete") statusCounts.complete += 1;
    else if (status === "partial") statusCounts.partial += 1;
    else statusCounts.missing += 1;
  }

  const totalTopics = topicEntries.length;
  const coveragePercentage =
    totalTopics > 0
      ? Math.round((statusCounts.complete / totalTopics) * 100)
      : 0;

  return {
    topicEntries,
    statusCounts,
    coveragePercentage,
  };
}

interface CoverageGridProps {
  readonly counts: StatusCounts;
}

function CoverageGrid({ counts }: CoverageGridProps) {
  return (
    <div className="grid grid-cols-3 gap-2 text-center">
      <div>
        <div className="text-2xl font-bold text-green-600">
          {counts.complete}
        </div>
        <div className="text-xs text-gray-600">Complete</div>
      </div>
      <div>
        <div className="text-2xl font-bold text-amber-600">
          {counts.partial}
        </div>
        <div className="text-xs text-gray-600">Partial</div>
      </div>
      <div>
        <div className="text-2xl font-bold text-gray-400">
          {counts.missing}
        </div>
        <div className="text-xs text-gray-600">Missing</div>
      </div>
    </div>
  );
}

interface TopicListProps {
  readonly entries: readonly [string, { readonly status?: string }][];
}

function TopicList({ entries }: TopicListProps) {
  return (
    <div className="pt-4 border-t border-gray-200 space-y-2 max-h-60 overflow-y-auto">
      {entries.map(([topic, data]) => {
        const rawStatus = data.status ?? "missing";
        const status = rawStatus.toLowerCase();
        let variant: "success" | "warning" | "default" = "default";
        if (status === "complete") variant = "success";
        else if (status === "partial") variant = "warning";

        return (
          <div key={topic} className="flex items-center justify-between text-sm">
            <span className="text-gray-700 truncate flex-1">
              {topic.replace(/_/g, " ")}
            </span>
            <Badge variant={variant} size="sm">
              {status}
            </Badge>
          </div>
        );
      })}
    </div>
  );
}

export function ArchitectureCoverageCard({
  coverage,
}: ArchitectureCoverageCardProps) {
  const { topicEntries, statusCounts, coveragePercentage } =
    useCoverageData(coverage);

  const updatedDate =
    coverage !== null && coverage !== undefined
      ? coverage.computedAt ?? ""
      : "";

  return (
    <Card>
      <CardHeader>
        <CardTitle>Architecture Coverage</CardTitle>
      </CardHeader>
      <CardContent>
        {topicEntries.length === 0 ? (
          <div className="text-center text-gray-500 py-8">
            No coverage data yet
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex items-center justify-center">
              <CoverageProgress percentage={coveragePercentage} />
            </div>

            <CoverageGrid counts={statusCounts} />

            <TopicList entries={topicEntries} />

            {updatedDate !== "" && (
              <p className="text-xs text-gray-500 text-center pt-2">
                Updated: {new Date(updatedDate).toLocaleString()}
              </p>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
