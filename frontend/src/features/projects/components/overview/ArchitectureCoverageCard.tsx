import { Card, CardHeader, CardTitle, CardContent, Badge } from "../../../../components/common";
import { CoverageProgress } from "./charts/CoverageProgress";

interface MindMapCoverage {
  version?: string;
  computedAt?: string;
  topics?: Record<string, { status?: string }>;
}

interface ArchitectureCoverageCardProps {
  coverage: MindMapCoverage | null | undefined;
}

export function ArchitectureCoverageCard({ coverage }: ArchitectureCoverageCardProps) {
  const topics = coverage?.topics || {};
  const topicEntries = Object.entries(topics);

  const statusCounts = {
    complete: 0,
    partial: 0,
    missing: 0,
  };

  for (const [, data] of topicEntries) {
    const status = data.status?.toLowerCase() || "missing";
    if (status === "complete") statusCounts.complete++;
    else if (status === "partial") statusCounts.partial++;
    else statusCounts.missing++;
  }

  const totalTopics = topicEntries.length;
  const coveragePercentage = totalTopics > 0
    ? Math.round((statusCounts.complete / totalTopics) * 100)
    : 0;

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

            <div className="grid grid-cols-3 gap-2 text-center">
              <div>
                <div className="text-2xl font-bold text-green-600">
                  {statusCounts.complete}
                </div>
                <div className="text-xs text-gray-600">Complete</div>
              </div>
              <div>
                <div className="text-2xl font-bold text-amber-600">
                  {statusCounts.partial}
                </div>
                <div className="text-xs text-gray-600">Partial</div>
              </div>
              <div>
                <div className="text-2xl font-bold text-gray-400">
                  {statusCounts.missing}
                </div>
                <div className="text-xs text-gray-600">Missing</div>
              </div>
            </div>

            <div className="pt-4 border-t border-gray-200 space-y-2 max-h-60 overflow-y-auto">
              {topicEntries.map(([topic, data]) => {
                const status = data.status?.toLowerCase() || "missing";
                let variant: "success" | "warning" | "default" = "default";
                if (status === "complete") variant = "success";
                else if (status === "partial") variant = "warning";

                return (
                  <div
                    key={topic}
                    className="flex items-center justify-between text-sm"
                  >
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

            {coverage?.computedAt && (
              <p className="text-xs text-gray-500 text-center pt-2">
                Updated: {new Date(coverage.computedAt).toLocaleString()}
              </p>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
