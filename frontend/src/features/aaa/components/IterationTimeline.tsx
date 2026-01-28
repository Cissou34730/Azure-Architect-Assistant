import type { IterationEvent, SourceCitation } from "../../../types/api";

interface IterationTimelineProps {
  readonly events: readonly IterationEvent[];
}

function IterationCitationList({ citations }: { readonly citations: readonly SourceCitation[] }) {
  if (citations.length === 0) return null;

  return (
    <div className="mt-3 text-xs text-gray-600">
      <p className="font-medium">Citations</p>
      <ul className="list-disc list-inside">
        {citations.map((citation, idx) => {
          const kind = citation.kind ?? "source";
          const url = citation.url?.trim() ?? "";
          const note = citation.note?.trim() ?? "";
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

function IterationItem({ event }: { readonly event: IterationEvent }) {
  const citations = event.citations;
  const { kind } = event;

  return (
    <li className="bg-white p-3 rounded-md border border-gray-200">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-medium text-gray-900">{kind}</p>
          {event.createdAt !== "" && (
            <p className="text-xs text-gray-500">{event.createdAt}</p>
          )}
        </div>
        <span className="text-xs text-gray-500">{event.id}</span>
      </div>

      {event.text !== "" && <p className="text-sm text-gray-700 mt-2 whitespace-pre-wrap">{event.text}</p>}

      <IterationCitationList citations={citations} />
    </li>
  );
}

export function IterationTimeline({ events }: IterationTimelineProps) {
  if (events.length === 0) {
    return <p className="text-gray-600">No iteration events yet.</p>;
  }

  const sortedEvents = [...events].sort((a, b) => a.createdAt.localeCompare(b.createdAt));

  return (
    <ul className="space-y-2">
      {sortedEvents.map((event, idx) => (
        <IterationItem key={event.id !== "" ? event.id : `it-${idx}`} event={event} />
      ))}
    </ul>
  );
}
