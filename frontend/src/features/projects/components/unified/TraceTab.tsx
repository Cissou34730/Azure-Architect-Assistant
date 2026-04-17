import { useEffect, useState } from "react";
import { traceApi } from "../../api/traceService";
import type { ProjectTraceEvent } from "../../types/trace";

interface TraceTabProps {
  readonly projectId: string;
  readonly lastUpdated: string;
}

function toTitleCase(value: string): string {
  return value
    .split(/[_\s-]+/)
    .filter((part) => part.length > 0)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function getEventSection(event: ProjectTraceEvent): string {
  const payload = event.payload;
  if (
    "update_keys" in payload ||
    "updateKeys" in payload ||
    event.eventType.includes("state")
  ) {
    return "State Updates";
  }
  if (
    event.eventType === "workflow_stage_result" ||
    "stageClassification" in payload ||
    "stage" in payload
  ) {
    return "Stage Classification";
  }
  if ("evidence" in payload || "consultedSources" in payload) {
    return "Research";
  }
  if ("toolCalls" in payload || event.eventType.includes("tool")) {
    return "Tool Calls";
  }
  if (
    "pendingChange" in payload ||
    "changeSetId" in payload ||
    event.eventType.includes("pending")
  ) {
    return "Pending Changes";
  }
  return "Workflow Trace";
}

function getEventSummaryLines(event: ProjectTraceEvent): readonly string[] {
  const payload = event.payload;
  const lines: string[] = [];

  if (typeof payload.stage === "string" && payload.stage.length > 0) {
    lines.push(payload.stage);
  }

  const updateKeys =
    (Array.isArray(payload.update_keys) ? payload.update_keys : undefined) ??
    (Array.isArray(payload.updateKeys) ? payload.updateKeys : undefined);
  if (updateKeys !== undefined && updateKeys.length > 0) {
    lines.push(updateKeys.join(", "));
  }

  if (typeof payload.changeSetId === "string" && payload.changeSetId.length > 0) {
    lines.push(`Pending change: ${payload.changeSetId}`);
  }

  if (Array.isArray(payload.evidence) && payload.evidence.length > 0) {
    lines.push(`Evidence packets: ${payload.evidence.length}`);
  }

  return lines;
}

function getRemainingPayload(event: ProjectTraceEvent): Record<string, unknown> {
  const remainingEntries = Object.entries(event.payload).filter(([key]) => {
    return !["stage", "update_keys", "updateKeys", "changeSetId", "evidence"].includes(key);
  });
  return Object.fromEntries(remainingEntries);
}

function TraceEventCard({ event }: { readonly event: ProjectTraceEvent }) {
  const section = getEventSection(event);
  const summaryLines = getEventSummaryLines(event);
  const remainingPayload = getRemainingPayload(event);
  const hasRemainingPayload = Object.keys(remainingPayload).length > 0;

  return (
    <li className="rounded-xl border border-border bg-card p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="space-y-1">
          <span className="inline-flex rounded-full border border-border px-2 py-1 text-xs font-semibold text-secondary">
            {section}
          </span>
          <p className="text-sm font-semibold text-foreground">{toTitleCase(event.eventType)}</p>
        </div>
        <p className="text-xs text-dim">{event.createdAt}</p>
      </div>
      {summaryLines.length > 0 && (
        <div className="mt-3 space-y-1">
          {summaryLines.map((line) => (
            <p key={line} className="text-sm text-secondary">
              {line}
            </p>
          ))}
        </div>
      )}
      {hasRemainingPayload && (
        <pre className="mt-3 overflow-x-auto rounded-lg bg-surface p-3 text-xs text-secondary">
          {JSON.stringify(remainingPayload, null, 2)}
        </pre>
      )}
    </li>
  );
}

export function TraceTab({ projectId, lastUpdated }: TraceTabProps) {
  const [events, setEvents] = useState<readonly ProjectTraceEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    const loadTrace = async () => {
      setLoading(true);
      try {
        const response = await traceApi.list(projectId);
        if (active) {
          setEvents(response.events);
          setError(null);
        }
      } catch (loadError) {
        if (active) {
          setError(loadError instanceof Error ? loadError.message : "Failed to load project trace.");
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    };

    void loadTrace();
    return () => {
      active = false;
    };
  }, [lastUpdated, projectId]);

  if (loading && events.length === 0) {
    return <div className="p-6 text-sm text-secondary">Loading workflow trace…</div>;
  }

  if (error !== null && events.length === 0) {
    return <div className="p-6 text-sm text-danger">{error}</div>;
  }

  return (
    <div className="flex h-full flex-col gap-4 overflow-y-auto p-4">
      <div className="rounded-xl border border-border bg-card p-4">
        <h2 className="text-lg font-semibold text-foreground">Workflow trace</h2>
        <p className="mt-1 text-sm text-secondary">
          Timeline of persisted execution events for the current project thread.
        </p>
      </div>

      {events.length === 0 ? (
        <div className="rounded-xl border border-border bg-card p-4 text-sm text-secondary">
          No trace events available yet.
        </div>
      ) : (
        <ul className="space-y-3">
          {events.map((event) => (
            <TraceEventCard key={event.id} event={event} />
          ))}
        </ul>
      )}
    </div>
  );
}
