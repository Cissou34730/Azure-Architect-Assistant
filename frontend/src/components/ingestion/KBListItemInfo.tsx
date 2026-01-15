import { KnowledgeBase, IngestionJob } from "../../types/ingestion";
import { StatusBadge } from "../common";
import { KBJobStatus } from "./KBJobStatus";

interface KBListItemInfoProps {
  readonly kb: KnowledgeBase;
  readonly job: IngestionJob | null | undefined;
}

export function KBListItemInfo({ kb, job }: KBListItemInfoProps) {
  const renderMetadata = () => {
    return (
      <div className="mt-2 flex items-center gap-4 text-xs text-gray-500">
        <span>ID: {kb.id}</span>
        {kb.sourceType !== undefined && (
          <span>Source: {kb.sourceType.replace("_", " ")}</span>
        )}
        <span>Priority: {kb.priority}</span>
        <span>Profiles: {kb.profiles.join(", ")}</span>
      </div>
    );
  };

  return (
    <div className="flex-1">
      <div className="flex items-center gap-3">
        <h3 className="text-lg font-semibold text-gray-900">{kb.name}</h3>
        <StatusBadge variant={kb.status === "active" ? "active" : "inactive"}>
          {kb.status}
        </StatusBadge>
        {kb.indexed === true && (
          <StatusBadge variant="active">Indexed</StatusBadge>
        )}
      </div>

      {kb.description !== undefined && kb.description !== "" && (
        <p className="mt-1 text-sm text-gray-600">{kb.description}</p>
      )}

      {renderMetadata()}

      {kb.lastIndexedAt !== undefined && (
        <div className="mt-1 text-xs text-gray-500">
          Last indexed: {new Date(kb.lastIndexedAt).toLocaleString()}
        </div>
      )}

      {job !== null && job !== undefined && <KBJobStatus job={job} />}
    </div>
  );
}
