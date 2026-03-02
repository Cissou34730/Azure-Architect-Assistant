import { Pin } from "lucide-react";
import type { WorkspaceTab } from "./workspace/types";

const TAB_BADGE_CLASS: Record<"input" | "artifact", string> = {
  input: "bg-info text-inverse border-info",
  artifact: "bg-brand text-inverse border-brand",
};

function TabBadge({ group }: { readonly group: "input" | "artifact" }) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase ${TAB_BADGE_CLASS[group]}`}
    >
      {group === "input" ? "Input" : "Artifact"}
    </span>
  );
}

export interface TabStripProps {
  readonly tabs: readonly WorkspaceTab[];
  readonly activeTabId: string;
  readonly onTabChange: (tabId: string) => void;
  readonly onCloseTab: (tabId: string) => void;
  readonly onTogglePin: (tabId: string) => void;
  readonly onReorderTab: (sourceId: string, targetId: string) => void;
  readonly draggingId: string | null;
  readonly setDraggingId: (value: string | null) => void;
}

export function TabStrip({
  tabs,
  activeTabId,
  onTabChange,
  onCloseTab,
  onTogglePin,
  onReorderTab,
  draggingId,
  setDraggingId,
}: TabStripProps) {
  return (
    <div className="border-b border-border bg-muted">
      <div className="flex items-stretch overflow-x-auto" role="tablist" aria-label="Workspace tabs">
        {tabs.length === 0 ? (
          <div className="px-3 py-2 text-xs text-secondary">No tabs open</div>
        ) : (
          tabs.map((tab) => {
          const isActive = tab.id === activeTabId;
          const isPinned = tab.pinned;
          const accentClass =
            tab.group === "input" ? "border-info" : "border-brand";
          const titleClass =
            tab.group === "input" ? "text-info-strong" : "text-brand-strong";
          return (
            <div
              key={tab.id}
              draggable
              onDragStart={() => {
                setDraggingId(tab.id);
              }}
              onDragOver={(event) => {
                event.preventDefault();
              }}
              onDrop={() => {
                if (draggingId !== null) {
                  onReorderTab(draggingId, tab.id);
                }
                setDraggingId(null);
              }}
              className={`group relative flex items-stretch border-r border-t-2 ${
                isActive
                  ? `bg-card ${accentClass} border-r-gray-200`
                  : "bg-muted border-transparent hover:bg-surface"
              }`}
            >
              <button
                type="button"
                onClick={() => { onTabChange(tab.id); }}
                className={`flex items-center gap-2 px-3 text-xs font-medium h-9 ${
                  isActive
                    ? "text-foreground border-b-2 border-border/30"
                    : "text-secondary"
                }`}
                role="tab"
                aria-selected={isActive}
              >
                <span className={`h-2 w-2 rounded-full ${tab.group === "input" ? "bg-info-soft0" : "bg-brand"}`} />
                <TabBadge group={tab.group} />
                <span className={`truncate max-w-56 ${titleClass}`}>{tab.title}</span>
              </button>
              <button
                type="button"
                onClick={(event) => {
                  event.stopPropagation();
                  onTogglePin(tab.id);
                }}
                aria-label={isPinned ? `Unpin ${tab.title}` : `Pin ${tab.title}`}
                className={`h-9 px-2 text-dim hover:text-secondary transition-opacity ${
                  isPinned ? "opacity-100" : "opacity-0 group-hover:opacity-100"
                }`}
              >
                <Pin className={`h-3.5 w-3.5 ${isPinned ? "text-brand" : ""}`} />
              </button>
              <button
                type="button"
                onClick={(event) => {
                  event.stopPropagation();
                  onCloseTab(tab.id);
                }}
                aria-label={`Close ${tab.title}`}
                className="h-9 px-2 text-dim hover:text-secondary opacity-0 group-hover:opacity-100 transition-opacity"
              >
                ×
              </button>
              {tab.dirty && (
                <span className="absolute right-2 top-1/2 -translate-y-1/2 text-[10px] text-brand group-hover:opacity-0 transition-opacity">
                  ●
                </span>
              )}
            </div>
          );
        })
        )}
      </div>
    </div>
  );
}
