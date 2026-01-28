import type { CandidateArchitecture, SourceCitation } from "../../../types/api";

interface CandidateArchitecturesProps {
  readonly candidates: readonly CandidateArchitecture[];
}

export function CandidateArchitectures({
  candidates,
}: CandidateArchitecturesProps) {
  if (candidates.length === 0) {
    return (
      <p className="text-gray-600">
        No candidates yet. Use the Agent chat to generate one.
      </p>
    );
  }

  return (
    <div className="space-y-3">
      {candidates.map((candidate, idx) => {
        const title = candidate.title ?? "Untitled";
        const summary = candidate.summary ?? "";
        const citations = candidate.sourceCitations ?? [];

        return (
          <div
            key={candidate.id !== "" ? candidate.id : `${title}-${String(idx)}`}
            className="bg-white p-4 rounded-md border border-gray-200"
          >
            <div className="flex items-start justify-between gap-3">
              <h4 className="font-semibold text-gray-900">{title}</h4>
              {candidate.id !== "" && (
                <span className="text-xs text-gray-500">{candidate.id}</span>
              )}
            </div>
            {summary !== "" && (
              <p className="text-sm text-gray-700 mt-2 whitespace-pre-wrap">
                {summary}
              </p>
            )}

            {citations.length > 0 && (
              <div className="mt-3 text-xs text-gray-600">
                <p className="font-medium">Citations</p>
                <ul className="list-disc list-inside">
                  {citations.map((citation: SourceCitation, cIdx: number) => {
                    const kind = citation.kind ?? "source";
                    const url = (citation.url ?? "").trim();
                    const note = (citation.note ?? "").trim();
                    return (
                      <li key={`${candidate.id ?? title}-cit-${String(cIdx)}`}>
                        {kind}
                        {url !== "" ? ` — ${url}` : ""}
                        {note !== "" ? ` (${note})` : ""}
                      </li>
                    );
                  })}
                </ul>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
