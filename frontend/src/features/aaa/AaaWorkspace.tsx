import { useMemo } from "react";
import { useProjectContext } from "../projects/context/ProjectContext";

type Requirement = {
  id?: string;
  category?: string;
  text?: string;
  ambiguity?: { isAmbiguous?: boolean; notes?: string };
  sources?: Array<{ documentId?: string; fileName?: string; excerpt?: string }>;
};

type ClarificationQuestion = {
  id?: string;
  question?: string;
  priority?: number;
  status?: string;
};

type IterationEvent = {
  id?: string;
  kind?: string;
  text?: string;
  citations?: Array<{ kind?: string; url?: string; note?: string }>;
  createdAt?: string;
};

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="bg-gray-50 p-4 rounded-md border border-gray-200">
      <h3 className="font-semibold text-lg mb-2">{title}</h3>
      <div className="space-y-2 text-sm">{children}</div>
    </div>
  );
}

export default function AaaWorkspace() {
  const {
    selectedProject,
    files,
    setFiles,
    handleUploadDocuments,
    handleAnalyzeDocuments,
    loading,
    loadingMessage,
    projectState,
  } = useProjectContext();

  const requirements = (projectState as any)?.requirements as Requirement[] | undefined;
  const clarificationQuestions = (projectState as any)?.clarificationQuestions as
    | ClarificationQuestion[]
    | undefined;
  const candidates = ((projectState as any)?.candidateArchitectures || []) as any[];
  const iterationEvents = ((projectState as any)?.iterationEvents || []) as
    | IterationEvent[]
    | undefined;

  const groupedRequirements = useMemo(() => {
    const groups: Record<string, Requirement[]> = {
      business: [],
      functional: [],
      nfr: [],
      other: [],
    };

    for (const r of requirements || []) {
      const category = (r?.category || "").toLowerCase();
      if (category === "business") groups.business.push(r);
      else if (category === "functional") groups.functional.push(r);
      else if (category === "nfr") groups.nfr.push(r);
      else groups.other.push(r);
    }

    return groups;
  }, [requirements]);

  if (!selectedProject) return null;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold mb-1">AAA Workspace</h2>
        <p className="text-sm text-gray-600">
          Upload/analyze project documents and review extracted requirements.
        </p>
        {loading && (
          <p className="text-sm text-gray-600 mt-2">
            {loadingMessage || "Working..."}
          </p>
        )}
      </div>

      <Section title="Upload & Analyze">
        <form onSubmit={handleUploadDocuments} className="space-y-3">
          <div>
            <label
              htmlFor="file-input"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Documents
            </label>
            <input
              id="file-input"
              type="file"
              multiple
              onChange={(e) => setFiles(e.target.files)}
              className="block w-full text-sm text-gray-700"
            />
          </div>

          <div className="flex gap-2">
            <button
              type="submit"
              disabled={!files || files.length === 0 || loading}
              className="bg-blue-600 text-white px-3 py-2 rounded-md hover:bg-blue-700 disabled:opacity-50 text-sm"
            >
              Upload
            </button>
            <button
              type="button"
              onClick={() => void handleAnalyzeDocuments()}
              disabled={loading}
              className="bg-green-600 text-white px-3 py-2 rounded-md hover:bg-green-700 disabled:opacity-50 text-sm"
            >
              Analyze
            </button>
          </div>
        </form>
      </Section>

      <Section title="Requirements Review">
        {!requirements || requirements.length === 0 ? (
          <p className="text-gray-600">
            No extracted requirements yet. Upload/analyze documents first.
          </p>
        ) : (
          <div className="space-y-4">
            {(
              [
                ["Business", groupedRequirements.business],
                ["Functional", groupedRequirements.functional],
                ["NFR", groupedRequirements.nfr],
                ["Other", groupedRequirements.other],
              ] as const
            ).map(([label, items]) => (
              <div key={label} className="space-y-2">
                <h4 className="font-semibold text-gray-800">{label}</h4>
                {items.length === 0 ? (
                  <p className="text-gray-500">None.</p>
                ) : (
                  <ul className="space-y-2">
                    {items.map((r) => {
                      const isAmbiguous = Boolean(r?.ambiguity?.isAmbiguous);
                      const notes = (r?.ambiguity?.notes || "").trim();
                      const text = (r?.text || "").trim();

                      return (
                        <li
                          key={r.id || `${label}-${text}`}
                          className="bg-white p-3 rounded-md border border-gray-200"
                        >
                          <div className="flex items-start justify-between gap-3">
                            <p className="text-gray-900">{text}</p>
                            {isAmbiguous && (
                              <span className="text-xs font-semibold text-yellow-700 bg-yellow-100 px-2 py-1 rounded">
                                Ambiguous
                              </span>
                            )}
                          </div>
                          {notes && (
                            <p className="text-xs text-gray-600 mt-1">
                              Notes: {notes}
                            </p>
                          )}
                          {Array.isArray(r.sources) && r.sources.length > 0 && (
                            <div className="mt-2 text-xs text-gray-600">
                              <p className="font-medium">Sources</p>
                              <ul className="list-disc list-inside">
                                {r.sources.map((s, idx) => (
                                  <li key={`${r.id || text}-src-${idx}`}>
                                    {(s.fileName || s.documentId || "Unknown source")}
                                    {s.excerpt ? ` — “${s.excerpt}”` : ""}
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </li>
                      );
                    })}
                  </ul>
                )}
              </div>
            ))}
          </div>
        )}
      </Section>

      <Section title="Clarification Questions">
        {!clarificationQuestions || clarificationQuestions.length === 0 ? (
          <p className="text-gray-600">
            No clarification questions yet.
          </p>
        ) : (
          <ul className="space-y-2">
            {clarificationQuestions
              .slice()
              .sort((a, b) => (a.priority ?? 999) - (b.priority ?? 999))
              .map((q) => (
                <li
                  key={q.id || q.question}
                  className="bg-white p-3 rounded-md border border-gray-200"
                >
                  <div className="flex items-start justify-between gap-3">
                    <p className="text-gray-900">{q.question}</p>
                    <span className="text-xs text-gray-600">
                      P{q.priority ?? "-"} • {q.status ?? "open"}
                    </span>
                  </div>
                </li>
              ))}
          </ul>
        )}
      </Section>
      <Section title="Candidate Architectures">
        {!Array.isArray(candidates) || candidates.length === 0 ? (
          <p className="text-gray-600">
            No candidates yet. Use the Agent chat to generate one.
          </p>
        ) : (
          <div className="space-y-3">
            {candidates.map((c) => {
              const title = String(c?.title || "Untitled");
              const summary = String(c?.summary || "");
              const citations = Array.isArray(c?.sourceCitations)
                ? (c.sourceCitations as any[])
                : [];

              return (
                <div
                  key={String(c?.id || title)}
                  className="bg-white p-4 rounded-md border border-gray-200"
                >
                  <div className="flex items-start justify-between gap-3">
                    <h4 className="font-semibold text-gray-900">{title}</h4>
                    {c?.id && (
                      <span className="text-xs text-gray-500">{String(c.id)}</span>
                    )}
                  </div>
                  {summary && (
                    <p className="text-sm text-gray-700 mt-2 whitespace-pre-wrap">
                      {summary}
                    </p>
                  )}

                  {citations.length > 0 && (
                    <div className="mt-3 text-xs text-gray-600">
                      <p className="font-medium">Citations</p>
                      <ul className="list-disc list-inside">
                        {citations.map((s, idx) => (
                          <li key={`${String(c?.id || title)}-cit-${idx}`}>
                            {String(s?.kind || "source")}
                            {s?.url ? ` — ${String(s.url)}` : ""}
                            {s?.note ? ` (${String(s.note)})` : ""}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </Section>

      <Section title="Iteration Timeline">
        {!iterationEvents || iterationEvents.length === 0 ? (
          <p className="text-gray-600">No iteration events yet.</p>
        ) : (
          <ul className="space-y-2">
            {iterationEvents
              .slice()
              .sort((a, b) => String(a.createdAt || "").localeCompare(String(b.createdAt || "")))
              .map((ev) => {
                const citations = Array.isArray(ev.citations) ? ev.citations : [];
                return (
                  <li
                    key={ev.id || `${ev.kind}-${ev.createdAt}`}
                    className="bg-white p-3 rounded-md border border-gray-200"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="font-medium text-gray-900">
                          {String(ev.kind || "event")}
                        </p>
                        {ev.createdAt && (
                          <p className="text-xs text-gray-500">{String(ev.createdAt)}</p>
                        )}
                      </div>
                      {ev.id && (
                        <span className="text-xs text-gray-500">{String(ev.id)}</span>
                      )}
                    </div>

                    {ev.text && (
                      <p className="text-sm text-gray-700 mt-2 whitespace-pre-wrap">
                        {String(ev.text)}
                      </p>
                    )}

                    {citations.length > 0 && (
                      <div className="mt-3 text-xs text-gray-600">
                        <p className="font-medium">Citations</p>
                        <ul className="list-disc list-inside">
                          {citations.map((s, idx) => (
                            <li key={`${String(ev.id || ev.createdAt)}-cit-${idx}`}>
                              {String(s?.kind || "source")}
                              {s?.url ? ` — ${String(s.url)}` : ""}
                              {s?.note ? ` (${String(s.note)})` : ""}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </li>
                );
              })}
          </ul>
        )}
      </Section>
    </div>
  );
}
