import { Badge } from "../../../../../components/common";
import type { AdrArtifact } from "../../../../../types/api";
import { getStatusVariant } from "./AdrUtils";

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
      className="hover:bg-gray-50 cursor-pointer"
    >
      <td className="px-4 py-3 text-sm text-gray-900">{adr.title}</td>
      <td className="px-4 py-3">
        <Badge variant={getStatusVariant(adr.status)} size="sm">
          {adr.status}
        </Badge>
      </td>
      <td className="px-4 py-3 text-sm text-gray-600">
        {adr.createdAt !== undefined
          ? new Date(adr.createdAt).toLocaleDateString()
          : "—"}
      </td>
      <td className="px-4 py-3 text-sm text-gray-600">
        {adr.relatedRequirementIds.length + adr.relatedDiagramIds.length}
      </td>
    </tr>
  );
}

interface AdrTableProps {
  readonly adrs: readonly AdrArtifact[];
  readonly onSelect: (adr: AdrArtifact) => void;
}

export function AdrTable({ adrs, onSelect }: AdrTableProps) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse">
        <thead>
          <tr className="bg-gray-50 border-b border-gray-200">
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-600 uppercase">
              Title
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-600 uppercase">
              Status
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-600 uppercase">
              Created
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-600 uppercase">
              Related
            </th>
          </tr>
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
