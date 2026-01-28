import { Card, CardContent, Badge } from "../../../../../components/common";
import type { AdrArtifact } from "../../../../../types/api";
import { getStatusVariant } from "./AdrUtils";

interface AdrGridItemProps {
  readonly adr: AdrArtifact;
  readonly onSelect: (adr: AdrArtifact) => void;
}

function AdrGridItem({ adr, onSelect }: AdrGridItemProps) {
  return (
    <Card
      hover
      onClick={() => {
        onSelect(adr);
      }}
    >
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-2 mb-2">
          <h3 className="font-medium text-gray-900 text-sm line-clamp-2 flex-1">
            {adr.title}
          </h3>
          <Badge variant={getStatusVariant(adr.status)} size="sm">
            {adr.status}
          </Badge>
        </div>

        {adr.context !== "" && (
          <p className="text-xs text-gray-600 line-clamp-3 mb-3">
            {adr.context}
          </p>
        )}

        <div className="flex items-center gap-2 text-xs text-gray-500">
          {adr.createdAt !== undefined && (
            <span>{new Date(adr.createdAt).toLocaleDateString()}</span>
          )}
          {adr.relatedRequirementIds.length > 0 && (
            <>
              <span>•</span>
              <span>{adr.relatedRequirementIds.length} requirements</span>
            </>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

interface AdrGridProps {
  readonly adrs: readonly AdrArtifact[];
  readonly onSelect: (adr: AdrArtifact) => void;
}

export function AdrGrid({ adrs, onSelect }: AdrGridProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {adrs.map((adr) => (
        <AdrGridItem
          key={`${adr.id}-${adr.title}`}
          adr={adr}
          onSelect={onSelect}
        />
      ))}
    </div>
  );
}
