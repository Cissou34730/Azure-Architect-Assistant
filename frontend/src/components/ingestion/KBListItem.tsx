/**
 * KB List Item Component
 * Single row in the KB list - refactored for Single Responsibility Principle
 */

import { KnowledgeBase, IngestionJob } from "../../types/ingestion";
import { useState } from "react";
import { KBListItemInfo } from "./KBListItemInfo";
import { KBActions } from "./KBActions";
import { KBItemDropdown } from "./KBItemDropdown";

interface KBListItemProps {
  readonly kb: KnowledgeBase;
  readonly job?: IngestionJob | null;
  readonly onViewProgress: (kbId: string) => void;
  readonly onStartIngestion: (kbId: string) => void;
  readonly onDelete: (kbId: string) => void;
  readonly onRefresh: () => void;
}

function getJobStates(job: IngestionJob | null | undefined) {
  const status = job?.status ?? "none";
  const isIngesting = status === "running" || status === "pending";
  
  // Can start if not already running/pending, not completed, and not paused
  const canStartIngestion = 
    status === "not_started" || 
    (status !== "running" && status !== "pending" && status !== "completed" && status !== "paused");

  return { 
    isIngesting, 
    isPaused: status === "paused", 
    canStartIngestion 
  };
}

export function KBListItem({
  kb,
  job,
  onViewProgress,
  onStartIngestion,
  onDelete,
  onRefresh,
}: KBListItemProps) {
  const [showActions, setShowActions] = useState(false);
  const { isIngesting, isPaused, canStartIngestion } = getJobStates(job);

  return (
    <div
      className="card hover:shadow-lg transition-shadow"
      role="article"
      aria-label={`Knowledge base: ${kb.name}`}
    >
      <div className="flex items-start justify-between">
        <KBListItemInfo kb={kb} job={job} />

        <div className="flex gap-2 ml-4">
          <KBActions
            kbId={kb.id}
            isIngesting={isIngesting}
            isPaused={isPaused}
            canStartIngestion={canStartIngestion}
            onViewProgress={onViewProgress}
            onStartIngestion={onStartIngestion}
            onRefresh={onRefresh}
          />
          <KBItemDropdown
            showActions={showActions}
            setShowActions={setShowActions}
            onDelete={() => {
              onDelete(kb.id);
            }}
          />
        </div>
      </div>
    </div>
  );
}
