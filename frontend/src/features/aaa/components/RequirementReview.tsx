import type { Requirement, SourceCitation } from "../../../types/api";

interface RequirementReviewProps {
  readonly requirements: readonly Requirement[];
  readonly groupedRequirements: {
    readonly business: readonly Requirement[];
    readonly functional: readonly Requirement[];
    readonly nfr: readonly Requirement[];
    readonly other: readonly Requirement[];
  };
}

function SourceItem({ source, index }: { readonly source: SourceCitation; readonly index: number }) {
  const fileName = source.fileName ?? "";
  const docId = source.documentId ?? "";
  const sourceLabel = fileName !== "" ? fileName : docId !== "" ? docId : "Unknown source";
  const excerpt = source.excerpt ?? "";

  return (
    <li key={`src-${String(index)}`}>
      {sourceLabel}
      {excerpt !== "" ? ` — “${excerpt}”` : ""}
    </li>
  );
}

function RequirementItem({ req }: { readonly req: Requirement }) {
  const isAmbiguous = req.ambiguity?.isAmbiguous === true;
  const notes = (req.ambiguity?.notes ?? "").trim();
  const text = (req.text ?? "").trim();

  return (
    <li className="bg-white p-3 rounded-md border border-gray-200">
      <div className="flex items-start justify-between gap-3">
        <p className="text-gray-900">{text}</p>
        {isAmbiguous && (
          <span className="text-xs font-semibold text-yellow-700 bg-yellow-100 px-2 py-1 rounded">Ambiguous</span>
        )}
      </div>
      {notes !== "" && <p className="text-xs text-gray-600 mt-1">Notes: {notes}</p>}
      {req.sources !== undefined &&
        req.sources.length > 0 && (
        <div className="mt-2 text-xs text-gray-600">
          <p className="font-medium">Sources</p>
          <ul className="list-disc list-inside">
            {req.sources.map((s, idx) => {
              const key = s.fileName !== undefined && s.fileName !== "" ? s.fileName : s.documentId !== undefined && s.documentId !== "" ? s.documentId : `src-${idx}`;
              return <SourceItem key={key} source={s} index={idx} />;
            })}
          </ul>
        </div>
      )}
    </li>
  );
}

export function RequirementReview({ requirements, groupedRequirements }: RequirementReviewProps) {
  if (requirements.length === 0) {
    return <p className="text-gray-600">No extracted requirements yet. Upload/analyze documents first.</p>;
  }

  const sections = [
    { label: "Business", items: groupedRequirements.business },
    { label: "Functional", items: groupedRequirements.functional },
    { label: "NFR", items: groupedRequirements.nfr },
    { label: "Other", items: groupedRequirements.other },
  ];

  return (
    <div className="space-y-4">
      {sections.map((section) => (
        <div key={section.label} className="space-y-2">
          <h4 className="font-semibold text-gray-800">{section.label}</h4>
          {section.items.length === 0 ? (
            <p className="text-gray-500">None.</p>
          ) : (
            <ul className="space-y-2">
              {section.items.map((r, idx) => (
                <RequirementItem key={r.id !== undefined && r.id !== "" ? r.id : `req-${String(idx)}`} req={r} />
              ))}
            </ul>
          )}
        </div>
      ))}
    </div>
  );
}
