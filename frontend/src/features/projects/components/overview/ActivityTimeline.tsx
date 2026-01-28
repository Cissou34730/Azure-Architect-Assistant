import { Card, CardHeader, CardTitle, CardContent, Badge } from "../../../../components/common";
import {
  FileText,
  Sparkles,
  AlertTriangle,
  Code,
  DollarSign,
  CheckCircle,
  Circle,
} from "lucide-react";
import type { IterationEvent } from "../../../../types/api";

interface ActivityTimelineProps {
  events: readonly IterationEvent[];
  maxEvents?: number;
}

const EVENT_ICONS: Record<string, { icon: typeof Circle; color: string }> = {
  analysis: { icon: CheckCircle, color: "text-blue-600 bg-blue-50" },
  candidate: { icon: Sparkles, color: "text-purple-600 bg-purple-50" },
  adr: { icon: FileText, color: "text-green-600 bg-green-50" },
  finding: { icon: AlertTriangle, color: "text-amber-600 bg-amber-50" },
  iac: { icon: Code, color: "text-cyan-600 bg-cyan-50" },
  cost: { icon: DollarSign, color: "text-green-600 bg-green-50" },
  default: { icon: Circle, color: "text-gray-600 bg-gray-50" },
};

function formatTimestamp(timestamp: string): string {
  try {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 8400000);

    if (diffMins < 1) return "just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  } catch {
    return timestamp;
  }
}

interface ActivityItemProps {
  event: IterationEvent;
}

function ActivityItem({ event }: ActivityItemProps) {
  const kind = event.kind.toLowerCase();
  const config = EVENT_ICONS[kind] ?? EVENT_ICONS.default;
  // eslint-disable-next-line @typescript-eslint/naming-convention
  const EventIcon = config.icon;
  const text = event.text;
  const citations = event.citations;

  return (
    <div className="relative pl-11">
      <div
        className={`absolute left-0 top-0 w-8 h-8 rounded-full flex items-center justify-center ${config.color}`}
      >
        <EventIcon className="h-4 w-4" />
      </div>

      <div>
        <div className="flex items-center gap-2 mb-1">
          <Badge variant="default" size="sm">
            {kind !== "" ? kind : "event"}
          </Badge>
          {event.createdAt !== "" && (
            <span className="text-xs text-gray-500">
              {formatTimestamp(event.createdAt)}
            </span>
          )}
        </div>

        {text !== "" && (
          <p className="text-sm text-gray-700 mb-2 line-clamp-3">{text}</p>
        )}

        {citations.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {citations.slice(0, 3).map((cit) => (
              <Badge key={cit.url ?? cit.note ?? "citation"} variant="info" size="sm">
                {cit.kind !== undefined && cit.kind !== "" ? cit.kind : "citation"}
              </Badge>
            ))}
            {citations.length > 3 && (
              <Badge variant="default" size="sm">
                +{citations.length - 3} more
              </Badge>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export function ActivityTimeline({
  events,
  maxEvents = 10,
}: ActivityTimelineProps) {
  const sortedEvents = [...events]
    .sort((a, b) => {
      const dateA = a.createdAt;
      const dateB = b.createdAt;
      return dateB.localeCompare(dateA);
    })
    .slice(0, maxEvents);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Recent Activity</CardTitle>
      </CardHeader>
      <CardContent>
        {sortedEvents.length === 0 ? (
          <div className="text-center text-gray-500 py-8">No activity yet</div>
        ) : (
          <div className="relative">
            <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-gray-200" />

            <div className="space-y-6">
              {sortedEvents.map((event) => (
                <ActivityItem key={event.id} event={event} />
              ))}
            </div>

            {events.length > maxEvents && (
              <div className="mt-4 text-center">
                <button className="text-sm text-blue-600 hover:text-blue-700 font-medium whitespace-nowrap">
                  View all activity ({events.length})
                </button>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
