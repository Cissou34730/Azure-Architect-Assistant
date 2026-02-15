import { TableVirtuoso } from "react-virtuoso";
import { Badge } from "../../../../../components/common";
import type { AdrArtifact } from "../../../../../types/api";
import { getStatusVariant } from "./AdrUtils";

const VIRTUALIZE_THRESHOLD = 20;

interface AdrTableItemProps {
  readonly adr: AdrArtifact;
  readonly onSelect: (adr: AdrArtifact) => void;
}

function AdrTableItem({ adr, onSelect }: AdrTableItemProps) {
  return (
    <tr
      onClick={() => {
        onSelect(adr);
      }}
      className="hover:bg-surface cursor-pointer"
    >
      <td className="px-4 py-3 text-sm text-foreground">{adr.title}</td>
      <td className="px-4 py-3">
        <Badge variant={getStatusVariant(adr.status)} size="sm">
          {adr.status}
        </Badge>
      </td>
      <td className="px-4 py-3 text-sm text-secondary">
        {adr.createdAt !== undefined
          ? new Date(adr.createdAt).toLocaleDateString()
          : "—"}
      </td>
      <td className="px-4 py-3 text-sm text-secondary">
        {adr.relatedRequirementIds.length + adr.relatedDiagramIds.length}
      </td>
    </tr>
  );
}

interface AdrTableProps {
  readonly adrs: readonly AdrArtifact[];
  readonly onSelect: (adr: AdrArtifact) => void;
}

function AdrTableHeader() {
  return <tr className="bg-surface border-b border-border">
    <th className="px-4 py-3 text-left text-xs font-medium text-secondary uppercase w-1/2">
      Title
    </th>
    <th className="px-4 py-3 text-left text-xs font-medium text-secondary uppercase">
      Status
    </th>
    <th className="px-4 py-3 text-left text-xs font-medium text-secondary uppercase">
      Created
    </th>
    <th className="px-4 py-3 text-left text-xs font-medium text-secondary uppercase">
      Related
    </th>
  </tr>
}

export function AdrTable({ adrs, onSelect }: AdrTableProps) {
  if (adrs.length > VIRTUALIZE_THRESHOLD) {
    return (
      <div className="overflow-x-auto border border-border rounded-lg">
        <TableVirtuoso
          useWindowScroll
          data={adrs}
          fixedHeaderContent={AdrTableHeader}
          itemContent={(_index, adr) => (
            <>
              <td className="px-4 py-3 text-sm text-foreground">{adr.title}</td>
              <td className="px-4 py-3">
                <Badge variant={getStatusVariant(adr.status)} size="sm">
                  {adr.status}
                </Badge>
              </td>
              <td className="px-4 py-3 text-sm text-secondary">
                {adr.createdAt !== undefined
                  ? new Date(adr.createdAt).toLocaleDateString()
                  : "—"}
              </td>
              <td className="px-4 py-3 text-sm text-secondary">
                {adr.relatedRequirementIds.length + adr.relatedDiagramIds.length}
              </td>
            </>
          )}
          components={{
            // eslint-disable-next-line @typescript-eslint/naming-convention -- react-virtuoso requires TableRow key and injects data-index
            TableRow: (props) => {
              const indexValue = props["data-index"];
              const item =
                typeof indexValue === "number" ? adrs[indexValue] : undefined;
              return (
                <tr
                  {...props}
                  onClick={() => {
                    if (item !== undefined) {
                      onSelect(item);
                    }
                  }}
                  className="hover:bg-surface cursor-pointer divide-y divide-gray-200"
                />
              );
            },
          }}
        />
      </div>
    );
  }

  return (
    <div className="overflow-x-auto border border-border rounded-lg">
      <table className="w-full border-collapse">
        <thead>
          <AdrTableHeader />
        </thead>
        <tbody className="divide-y divide-gray-200">
          {adrs.map((adr) => (
            <AdrTableItem
              key={`${adr.id}-${adr.title}`}
              adr={adr}
              onSelect={onSelect}
            />
          ))}
        </tbody>
      </table>
    </div>
  );
}

