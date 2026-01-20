import { useMemo } from "react";
import { useProjectContext } from "../projects/context/useProjectContext";

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

type Adr = {
  id?: string;
  title?: string;
  status?: string;
  context?: string;
  decision?: string;
  consequences?: string;
  relatedRequirementIds?: string[];
  relatedMindMapNodeIds?: string[];
  relatedDiagramIds?: string[];
  relatedWafEvidenceIds?: string[];
  missingEvidenceReason?: string;
  supersedesAdrId?: string;
  createdAt?: string;
  sourceCitations?: Array<{ kind?: string; url?: string; note?: string }>;
};

type Finding = {
  id?: string;
  title?: string;
  severity?: string;
  description?: string;
  remediation?: string;
  wafPillar?: string;
  wafTopic?: string;
  relatedRequirementIds?: string[];
  sourceCitations?: Array<{ kind?: string; url?: string; note?: string }>;
  createdAt?: string;
};

type IacFile = {
  path?: string;
  format?: string;
  content?: string;
};

type IacArtifact = {
  id?: string;
  createdAt?: string;
  files?: IacFile[];
  validationResults?: Array<{ tool?: string; status?: string; output?: string }>;
};

type CostLineItem = {
  id?: string;
  name?: string;
  monthlyQuantity?: number;
  unitPrice?: number;
  monthlyCost?: number;
  unitOfMeasure?: string;
};

type CostEstimate = {
  id?: string;
  createdAt?: string;
  currencyCode?: string;
  totalMonthlyCost?: number;
  lineItems?: CostLineItem[];
  pricingGaps?: Array<{ name?: string; reason?: string }>;
  variancePct?: number;
};

type MindMapCoverage = {
  version?: string;
  computedAt?: string;
  topics?: Record<string, { status?: string }>;
};

type TraceabilityLink = {
  id?: string;
  fromType?: string;
  fromId?: string;
  toType?: string;
  toId?: string;
};

type TraceabilityIssue = {
  id?: string;
  kind?: string;
  message?: string;
  linkId?: string;
  createdAt?: string;
};

function downloadTextFile(fileName: string, content: string) {
  const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = fileName;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

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
  const adrs = ((projectState as any)?.adrs || []) as Adr[];
  const findings = ((projectState as any)?.findings || []) as Finding[];
  const iacArtifacts = ((projectState as any)?.iacArtifacts || []) as IacArtifact[];
  const costEstimates = ((projectState as any)?.costEstimates || []) as CostEstimate[];
  const iterationEvents = ((projectState as any)?.iterationEvents || []) as
    | IterationEvent[]
    | undefined;

  const mindMapCoverage = (projectState as any)?.mindMapCoverage as
    | MindMapCoverage
    | undefined;
  const traceabilityLinks = ((projectState as any)?.traceabilityLinks || []) as TraceabilityLink[];
  const traceabilityIssues = ((projectState as any)?.traceabilityIssues || []) as TraceabilityIssue[];

  const coverageTopics = useMemo(() => {
    const topics = mindMapCoverage?.topics;
    if (!topics || typeof topics !== "object") return [];

    const entries = Object.entries(topics).map(([key, value]) => {
      const status = String((value as any)?.status || "not-addressed");
      return { key, status };
    });

    const order = (key: string) => {
      const match = key.match(/^(\d+)_/);
      return match ? Number(match[1]) : 999;
    };

    entries.sort((a, b) => {
      const ao = order(a.key);
      const bo = order(b.key);
      if (ao !== bo) return ao - bo;
      return a.key.localeCompare(b.key);
    });

    return entries;
  }, [mindMapCoverage]);

  const traceabilityGroups = useMemo(() => {
    const groups: Record<string, TraceabilityLink[]> = {};
    for (const link of traceabilityLinks || []) {
      const fromType = String(link?.fromType || "").trim() || "unknown";
      const fromId = String(link?.fromId || "").trim() || "unknown";
      const key = `${fromType}:${fromId}`;
      if (!groups[key]) groups[key] = [];
      groups[key].push(link);
    }
    const keys = Object.keys(groups).sort((a, b) => a.localeCompare(b));
    return keys.map((k) => ({ key: k, links: groups[k] }));
  }, [traceabilityLinks]);

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

      <Section title="ADRs">
        {!Array.isArray(adrs) || adrs.length === 0 ? (
          <p className="text-gray-600">
            No ADRs yet. Use the Agent chat to create one.
          </p>
        ) : (
          <div className="space-y-3">
            {adrs
              .slice()
              .sort((a, b) =>
                String(a.createdAt || "").localeCompare(String(b.createdAt || ""))
              )
              .map((adr) => {
                const title = String(adr?.title || "Untitled ADR");
                const status = String(adr?.status || "draft");
                const citations = Array.isArray(adr?.sourceCitations)
                  ? (adr.sourceCitations as any[])
                  : [];

                return (
                  <div
                    key={String(adr?.id || title)}
                    className="bg-white p-4 rounded-md border border-gray-200"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <h4 className="font-semibold text-gray-900">{title}</h4>
                        <p className="text-xs text-gray-600 mt-1">{status}</p>
                      </div>
                      {adr?.id && (
                        <span className="text-xs text-gray-500">
                          {String(adr.id)}
                        </span>
                      )}
                    </div>

                    {adr?.supersedesAdrId && (
                      <p className="text-xs text-gray-600 mt-2">
                        Supersedes: {String(adr.supersedesAdrId)}
                      </p>
                    )}
                    {adr?.createdAt && (
                      <p className="text-xs text-gray-500 mt-1">
                        {String(adr.createdAt)}
                      </p>
                    )}

                    {adr?.context && (
                      <div className="mt-3">
                        <p className="text-xs font-medium text-gray-700">Context</p>
                        <p className="text-sm text-gray-700 whitespace-pre-wrap">
                          {String(adr.context)}
                        </p>
                      </div>
                    )}
                    {adr?.decision && (
                      <div className="mt-3">
                        <p className="text-xs font-medium text-gray-700">Decision</p>
                        <p className="text-sm text-gray-700 whitespace-pre-wrap">
                          {String(adr.decision)}
                        </p>
                      </div>
                    )}
                    {adr?.consequences && (
                      <div className="mt-3">
                        <p className="text-xs font-medium text-gray-700">Consequences</p>
                        <p className="text-sm text-gray-700 whitespace-pre-wrap">
                          {String(adr.consequences)}
                        </p>
                      </div>
                    )}

                    {(Array.isArray(adr?.relatedRequirementIds) &&
                      adr.relatedRequirementIds.length > 0) && (
                      <div className="mt-3 text-xs text-gray-600">
                        <p className="font-medium">Linked requirements</p>
                        <ul className="list-disc list-inside">
                          {adr.relatedRequirementIds.map((id) => (
                            <li key={`${String(adr.id || title)}-req-${id}`}>{id}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {(Array.isArray(adr?.relatedDiagramIds) &&
                      adr.relatedDiagramIds.length > 0) && (
                      <div className="mt-3 text-xs text-gray-600">
                        <p className="font-medium">Linked diagrams</p>
                        <ul className="list-disc list-inside">
                          {adr.relatedDiagramIds.map((id) => (
                            <li key={`${String(adr.id || title)}-dia-${id}`}>{id}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {(Array.isArray(adr?.relatedWafEvidenceIds) &&
                      adr.relatedWafEvidenceIds.length > 0) && (
                      <div className="mt-3 text-xs text-gray-600">
                        <p className="font-medium">WAF evidence</p>
                        <ul className="list-disc list-inside">
                          {adr.relatedWafEvidenceIds.map((id) => (
                            <li key={`${String(adr.id || title)}-waf-${id}`}>{id}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {adr?.missingEvidenceReason && (
                      <p className="text-xs text-gray-600 mt-3">
                        Missing evidence reason: {String(adr.missingEvidenceReason)}
                      </p>
                    )}

                    {citations.length > 0 && (
                      <div className="mt-3 text-xs text-gray-600">
                        <p className="font-medium">Citations</p>
                        <ul className="list-disc list-inside">
                          {citations.map((s, idx) => (
                            <li key={`${String(adr?.id || title)}-cit-${idx}`}>
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

      <Section title="Findings">
        {!Array.isArray(findings) || findings.length === 0 ? (
          <p className="text-gray-600">No findings yet. Run validation via Agent chat.</p>
        ) : (
          <div className="space-y-3">
            {findings
              .slice()
              .sort((a, b) =>
                String(a.createdAt || "").localeCompare(String(b.createdAt || ""))
              )
              .map((f) => {
                const title = String(f?.title || "Untitled finding");
                const severity = String(f?.severity || "");
                const citations = Array.isArray(f?.sourceCitations)
                  ? (f.sourceCitations as any[])
                  : [];
                const reqIds = Array.isArray(f?.relatedRequirementIds)
                  ? (f.relatedRequirementIds as string[])
                  : [];

                return (
                  <div
                    key={String(f?.id || title)}
                    className="bg-white p-4 rounded-md border border-gray-200"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <h4 className="font-semibold text-gray-900">{title}</h4>
                        <p className="text-xs text-gray-600 mt-1">
                          {severity ? `Severity: ${severity}` : ""}
                          {(f?.wafPillar || f?.wafTopic) && severity ? " • " : ""}
                          {f?.wafPillar ? String(f.wafPillar) : ""}
                          {f?.wafTopic ? ` — ${String(f.wafTopic)}` : ""}
                        </p>
                      </div>
                      {f?.id && (
                        <span className="text-xs text-gray-500">{String(f.id)}</span>
                      )}
                    </div>

                    {f?.createdAt && (
                      <p className="text-xs text-gray-500 mt-1">{String(f.createdAt)}</p>
                    )}

                    {f?.description && (
                      <div className="mt-3">
                        <p className="text-xs font-medium text-gray-700">Description</p>
                        <p className="text-sm text-gray-700 whitespace-pre-wrap">
                          {String(f.description)}
                        </p>
                      </div>
                    )}

                    {f?.remediation && (
                      <div className="mt-3">
                        <p className="text-xs font-medium text-gray-700">Remediation</p>
                        <p className="text-sm text-gray-700 whitespace-pre-wrap">
                          {String(f.remediation)}
                        </p>
                      </div>
                    )}

                    {reqIds.length > 0 && (
                      <div className="mt-3 text-xs text-gray-600">
                        <p className="font-medium">Linked requirements</p>
                        <ul className="list-disc list-inside">
                          {reqIds.map((id) => (
                            <li key={`${String(f?.id || title)}-req-${id}`}>{id}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {citations.length > 0 && (
                      <div className="mt-3 text-xs text-gray-600">
                        <p className="font-medium">Citations</p>
                        <ul className="list-disc list-inside">
                          {citations.map((s, idx) => (
                            <li key={`${String(f?.id || title)}-cit-${idx}`}>
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

      <Section title="IaC">
        {!Array.isArray(iacArtifacts) || iacArtifacts.length === 0 ? (
          <p className="text-gray-600">No IaC artifacts yet. Generate via Agent chat.</p>
        ) : (
          <div className="space-y-3">
            {iacArtifacts
              .slice()
              .sort((a, b) =>
                String(a.createdAt || "").localeCompare(String(b.createdAt || ""))
              )
              .map((a) => {
                const files = Array.isArray(a?.files) ? a.files : [];
                const validations = Array.isArray(a?.validationResults)
                  ? a.validationResults
                  : [];
                return (
                  <div
                    key={String(a?.id || a?.createdAt || "iac")}
                    className="bg-white p-4 rounded-md border border-gray-200"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <h4 className="font-semibold text-gray-900">IaC Artifact</h4>
                        {a?.createdAt && (
                          <p className="text-xs text-gray-500 mt-1">{String(a.createdAt)}</p>
                        )}
                      </div>
                      {a?.id && (
                        <span className="text-xs text-gray-500">{String(a.id)}</span>
                      )}
                    </div>

                    {files.length > 0 && (
                      <div className="mt-3 text-sm">
                        <p className="text-xs font-medium text-gray-700">Files</p>
                        <ul className="space-y-2 mt-2">
                          {files.map((f, idx) => {
                            const path = String(f?.path || `file-${idx}`);
                            const content = String(f?.content || "");
                            const format = String(f?.format || "");
                            return (
                              <li
                                key={`${String(a?.id || "iac")}-file-${idx}-${path}`}
                                className="flex items-center justify-between gap-3"
                              >
                                <div className="text-xs text-gray-700">
                                  <span className="font-medium">{path}</span>
                                  {format ? ` (${format})` : ""}
                                </div>
                                <button
                                  type="button"
                                  disabled={!content}
                                  onClick={() => downloadTextFile(path, content)}
                                  className="bg-blue-600 text-white px-3 py-1 rounded-md hover:bg-blue-700 disabled:opacity-50 text-xs"
                                >
                                  Download
                                </button>
                              </li>
                            );
                          })}
                        </ul>
                      </div>
                    )}

                    {validations.length > 0 && (
                      <div className="mt-4 text-xs text-gray-600">
                        <p className="font-medium">Validation</p>
                        <ul className="list-disc list-inside">
                          {validations.map((v, idx) => (
                            <li key={`${String(a?.id || "iac")}-val-${idx}`}>
                              {String(v?.tool || "validator")}: {String(v?.status || "")}
                              {v?.output ? ` — ${String(v.output)}` : ""}
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

      <Section title="Cost Estimates">
        {!Array.isArray(costEstimates) || costEstimates.length === 0 ? (
          <p className="text-gray-600">No cost estimates yet. Generate via Agent chat.</p>
        ) : (
          <div className="space-y-3">
            {costEstimates
              .slice()
              .sort((a, b) =>
                String(a.createdAt || "").localeCompare(String(b.createdAt || ""))
              )
              .map((c) => {
                const currency = String(c?.currencyCode || "USD");
                const total = typeof c?.totalMonthlyCost === "number" ? c.totalMonthlyCost : 0;
                const lines = Array.isArray(c?.lineItems) ? c.lineItems : [];
                const gaps = Array.isArray(c?.pricingGaps) ? c.pricingGaps : [];
                return (
                  <div
                    key={String(c?.id || c?.createdAt || "cost")}
                    className="bg-white p-4 rounded-md border border-gray-200"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <h4 className="font-semibold text-gray-900">Cost Estimate</h4>
                        <p className="text-sm text-gray-700 mt-1">
                          {currency} {total.toFixed(2)} / month
                          {typeof c?.variancePct === "number"
                            ? ` (variance ${c.variancePct.toFixed(1)}%)`
                            : ""}
                        </p>
                        {c?.createdAt && (
                          <p className="text-xs text-gray-500 mt-1">{String(c.createdAt)}</p>
                        )}
                      </div>
                      {c?.id && (
                        <span className="text-xs text-gray-500">{String(c.id)}</span>
                      )}
                    </div>

                    {lines.length > 0 && (
                      <div className="mt-3 text-xs text-gray-600">
                        <p className="font-medium">Line items</p>
                        <ul className="list-disc list-inside">
                          {lines.map((li, idx) => (
                            <li key={`${String(c?.id || "cost")}-li-${idx}`}>
                              {String(li?.name || "item")}: {currency} {Number(li?.monthlyCost || 0).toFixed(2)}
                              {li?.unitOfMeasure
                                ? ` (${String(li.unitOfMeasure)})`
                                : ""}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {gaps.length > 0 && (
                      <div className="mt-3 text-xs text-gray-600">
                        <p className="font-medium">Pricing gaps</p>
                        <ul className="list-disc list-inside">
                          {gaps.map((g, idx) => (
                            <li key={`${String(c?.id || "cost")}-gap-${idx}`}>
                              {String(g?.name || "item")}: {String(g?.reason || "missing")}
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

      <Section title="Mind Map Coverage">
        {coverageTopics.length === 0 ? (
          <p className="text-gray-600">No coverage computed yet.</p>
        ) : (
          <div className="space-y-2">
            {mindMapCoverage?.computedAt && (
              <p className="text-xs text-gray-500">
                Computed at: {String(mindMapCoverage.computedAt)}
              </p>
            )}
            <ul className="space-y-2">
              {coverageTopics.map((t) => (
                <li
                  key={t.key}
                  className="bg-white p-3 rounded-md border border-gray-200 flex items-start justify-between gap-3"
                >
                  <span className="text-sm text-gray-900">{t.key}</span>
                  <span className="text-xs text-gray-600">{t.status}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </Section>

      <Section title="Traceability">
        {!Array.isArray(traceabilityLinks) || traceabilityLinks.length === 0 ? (
          <p className="text-gray-600">No traceability links yet.</p>
        ) : (
          <div className="space-y-3">
            {traceabilityGroups.map((g) => (
              <div
                key={g.key}
                className="bg-white p-4 rounded-md border border-gray-200"
              >
                <h4 className="font-semibold text-gray-900">{g.key}</h4>
                <ul className="mt-2 space-y-1 text-xs text-gray-700">
                  {g.links.map((l, idx) => (
                    <li key={`${g.key}-${String(l?.id || idx)}`}
                      className="flex items-start justify-between gap-3"
                    >
                      <span>
                        → {String(l?.toType || "unknown")}:{String(l?.toId || "unknown")}
                      </span>
                      {l?.id && (
                        <span className="text-gray-500">{String(l.id)}</span>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        )}

        {Array.isArray(traceabilityIssues) && traceabilityIssues.length > 0 && (
          <div className="mt-3 text-xs text-gray-600">
            <p className="font-medium">Issues</p>
            <ul className="list-disc list-inside">
              {traceabilityIssues.map((i, idx) => (
                <li key={String(i?.id || idx)}>
                  {String(i?.kind || "issue")}: {String(i?.message || "")}
                  {i?.linkId ? ` (link ${String(i.linkId)})` : ""}
                </li>
              ))}
            </ul>
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
