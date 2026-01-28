import type { AdrArtifact, SourceCitation } from "../../../types/api";

interface AdrListProps {
  readonly adrs: readonly AdrArtifact[];
}

interface AdrItemProps {
  readonly adr: AdrArtifact;
  readonly index: number;
}

function CitationList({ citations, adrId }: { readonly citations: readonly SourceCitation[]; readonly adrId: string }) {
  if (citations.length === 0) return null;
  return (
    <div className="mt-3 text-xs text-gray-600">
      <p className="font-medium">Citations</p>
      <ul className="list-disc list-inside">
        {citations.map((citation, cIdx) => {
          const kind = citation.kind ?? "source";
          const url = (citation.url ?? "").trim();
          const note = (citation.note ?? "").trim();
          return (
            <li key={`${adrId}-cit-${String(cIdx)}`}>
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

function RelatedLinks({ title, ids, adrId, prefix }: { readonly title: string; readonly ids: readonly string[]; readonly adrId: string; readonly prefix: string }) {
  if (ids.length === 0) return null;
  return (
    <div className="mt-3 text-xs text-gray-600">
      <p className="font-medium">{title}</p>
      <ul className="list-disc list-inside">
        {ids.map((id) => (
          <li key={`${adrId}-${prefix}-${id}`}>{id}</li>
        ))}
      </ul>
    </div>
  );
}

function AdrHeader({ adr, title }: { readonly adr: AdrArtifact; readonly title: string }) {
  return (
    <div className="flex items-start justify-between gap-3">
      <div>
        <h4 className="font-semibold text-gray-900">{title}</h4>
        <p className="text-xs text-gray-600 mt-1">{adr.status}</p>
      </div>
      {adr.id !== "" && (
        <span className="text-xs text-gray-500">{adr.id}</span>
      )}
    </div>
  );
}

function AdrMetadata({ adr }: { readonly adr: AdrArtifact }) {
  const hasSupersedes = adr.supersedesAdrId !== undefined && adr.supersedesAdrId !== "";
  const hasCreatedAt = adr.createdAt !== undefined && adr.createdAt !== "";
  
  if (!hasSupersedes && !hasCreatedAt) return null;

  return (
    <>
      {hasSupersedes && (
        <p className="text-xs text-gray-600 mt-2">Supersedes: {adr.supersedesAdrId}</p>
      )}
      {hasCreatedAt && (
        <p className="text-xs text-gray-500 mt-1">{adr.createdAt}</p>
      )}
    </>
  );
}

function AdrContentSection({ label, content }: { readonly label: string; readonly content: string }) {
  if (content === "") return null;
  return (
    <div className="mt-3">
      <p className="text-xs font-medium text-gray-700">{label}</p>
      <p className="text-sm text-gray-700 whitespace-pre-wrap">{content}</p>
    </div>
  );
}

function AdrItem({ adr, index }: AdrItemProps) {
  const title = adr.title.trim() !== "" ? adr.title : "Untitled ADR";
  const idValue = adr.id !== "" ? adr.id : `${title}-${String(index)}`;

  const hasMissingReason =
    adr.missingEvidenceReason !== undefined && adr.missingEvidenceReason !== "";

  return (
    <div className="bg-white p-4 rounded-md border border-gray-200">
      <AdrHeader adr={adr} title={title} />
      <AdrMetadata adr={adr} />

      <AdrContentSection label="Context" content={adr.context} />
      <AdrContentSection label="Decision" content={adr.decision} />
      <AdrContentSection label="Consequences" content={adr.consequences} />

      <RelatedLinks
        title="Linked requirements"
        ids={adr.relatedRequirementIds}
        adrId={idValue}
        prefix="req"
      />
      <RelatedLinks
        title="Linked diagrams"
        ids={adr.relatedDiagramIds}
        adrId={idValue}
        prefix="dia"
      />
      <RelatedLinks
        title="WAF evidence"
        ids={adr.relatedWafEvidenceIds}
        adrId={idValue}
        prefix="waf"
      />

      {hasMissingReason && (
        <p className="text-xs text-gray-600 mt-3">
          Missing evidence reason: {adr.missingEvidenceReason}
        </p>
      )}

      <CitationList citations={adr.sourceCitations} adrId={idValue} />
    </div>
  );
}

export function AdrList({ adrs }: AdrListProps) {
  if (adrs.length === 0) {
    return (
      <p className="text-gray-600">No ADRs yet. Use the Agent chat to create one.</p>
    );
  }

  const sortedAdrs = [...adrs].sort((a, b) =>
    (a.createdAt ?? "").localeCompare(b.createdAt ?? "")
  );

  return (
    <div className="space-y-3">
      {sortedAdrs.map((adr, index) => (
        <AdrItem key={adr.id !== "" ? adr.id : `adr-${String(index)}`} adr={adr} index={index} />
      ))}
    </div>
  );
}
