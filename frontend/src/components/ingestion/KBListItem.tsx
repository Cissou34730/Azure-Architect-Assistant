/**
 * KB List Item Component
 * Single row in the KB list - refactored for Single Responsibility Principle
 */

import { KnowledgeBase, IngestionJob } from "../../types/ingestion";
import { useState, useRef, useEffect } from "react";
import { Button, StatusBadge } from "../common";
import { KBJobStatus } from "./KBJobStatus";
import { KBJobControls } from "./KBJobControls";

interface KBListItemProps {
  kb: KnowledgeBase;
  job?: IngestionJob | null;
  onViewProgress: (kbId: string) => void;
  onStartIngestion: (kbId: string) => void;
  onDelete: (kbId: string) => void;
  onRefresh: () => void;
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
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Job status helpers
  const isNotStarted = job?.status === "not_started";
  const isIngesting =
    (job?.status === "running" || job?.status === "pending") && !isNotStarted;
  const isPaused = job?.status === "paused";
  const isCompleted = job?.status === "completed";
  const canStartIngestion =
    isNotStarted || (!isIngesting && !isCompleted && !isPaused);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setShowActions(false);
      }
    };

    if (showActions) {
      document.addEventListener("mousedown", handleClickOutside);
      return () =>
        document.removeEventListener("mousedown", handleClickOutside);
    }
    return undefined;
  }, [showActions]);

  // Keyboard navigation for dropdown
  const handleKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === "Escape") {
      setShowActions(false);
    }
  };

  const handleDelete = () => {
    setShowActions(false);
    onDelete(kb.id);
  };

  return (
    <div
      className="card hover:shadow-lg transition-shadow"
      role="article"
      aria-label={`Knowledge base: ${kb.name}`}
    >
      <div className="flex items-start justify-between">
        {/* Left: KB Information */}
        <div className="flex-1">
          {/* KB Header */}
          <div className="flex items-center gap-3">
            <h3 className="text-lg font-semibold text-gray-900">{kb.name}</h3>
            <StatusBadge
              variant={kb.status === "active" ? "active" : "inactive"}
            >
              {kb.status}
            </StatusBadge>
            {kb.indexed && <StatusBadge variant="active">Indexed</StatusBadge>}
          </div>

          {/* KB Description */}
          {kb.description && (
            <p className="mt-1 text-sm text-gray-600">{kb.description}</p>
          )}

          {/* KB Metadata */}
          <div className="mt-2 flex items-center gap-4 text-xs text-gray-500">
            <span>ID: {kb.id}</span>
            {kb.source_type && (
              <span>Source: {kb.source_type.replace("_", " ")}</span>
            )}
            <span>Priority: {kb.priority}</span>
            <span>Profiles: {kb.profiles.join(", ")}</span>
          </div>

          {/* Last Indexed Timestamp */}
          {kb.last_indexed_at && (
            <div className="mt-1 text-xs text-gray-500">
              Last indexed: {new Date(kb.last_indexed_at).toLocaleString()}
            </div>
          )}

          {/* Job Status and Metrics */}
          {job && <KBJobStatus job={job} />}
        </div>

        {/* Right: Actions */}
        <div className="flex gap-2 ml-4">
          {/* Primary Action Button */}
          {isIngesting || isPaused ? (
            <Button
              variant="primary"
              size="sm"
              onClick={() => onViewProgress(kb.id)}
            >
              View Progress
            </Button>
          ) : canStartIngestion ? (
            <Button
              variant="success"
              size="sm"
              onClick={() => onStartIngestion(kb.id)}
            >
              Start Ingestion
            </Button>
          ) : null}

          {/* Job Controls */}
          {(isIngesting || isPaused) && (
            <KBJobControls
              kbId={kb.id}
              isRunning={isIngesting}
              isPaused={isPaused}
              onRefresh={onRefresh}
              onViewProgress={onViewProgress}
            />
          )}

          {/* More Actions Menu */}
          <div className="relative" ref={dropdownRef}>
            <button
              onClick={() => setShowActions(!showActions)}
              onKeyDown={handleKeyDown}
              className="px-2 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded-button"
              aria-label="More actions"
              aria-expanded={showActions ? "true" : "false"}
              aria-haspopup="menu"
            >
              <svg
                className="w-5 h-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z"
                />
              </svg>
            </button>

            {showActions && (
              <div
                className="absolute right-0 mt-1 w-48 bg-white rounded-button shadow-lg border border-gray-200 z-20"
                role="menu"
                aria-orientation="vertical"
              >
                <button
                  onClick={handleDelete}
                  className="w-full px-4 py-2 text-left text-sm text-red-600 hover:bg-red-50 rounded-button"
                  role="menuitem"
                >
                  Delete Knowledge Base
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
