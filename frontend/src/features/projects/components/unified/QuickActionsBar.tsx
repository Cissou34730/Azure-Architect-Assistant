import { Upload, Sparkles, FileText, Download } from "lucide-react";
import { useState } from "react";
import { ActionButton } from "./QuickActionsBar/ActionButton";
import { ProjectIdentity } from "./QuickActionsBar/ProjectIdentity";

interface QuickActionsBarProps {
  readonly projectName: string;
  readonly onUploadClick: () => void;
  readonly onGenerateDiagramClick: () => void;
  readonly onCreateAdrClick: () => void;
  readonly onExportClick: () => void;
  readonly onMenuClick?: () => void;
}

export function QuickActionsBar({
  projectName,
  onUploadClick,
  onGenerateDiagramClick,
  onCreateAdrClick,
  onExportClick,
  onMenuClick,
}: QuickActionsBarProps) {
  const [showTooltips] = useState(false);

  return (
    <div className="sticky top-0 z-10 bg-white border-b border-gray-200 shadow-sm">
      <div className="flex items-center justify-between px-6 py-3">
        {/* Left: Mobile menu + Project name */}
        <ProjectIdentity projectName={projectName} onMenuClick={onMenuClick} />

        {/* Right: Action buttons */}
        <div className="flex items-center gap-2">
          {/* Desktop buttons */}
          <div className="hidden md:flex items-center gap-2">
            <ActionButton
              icon={Upload}
              label="Upload"
              onClick={onUploadClick}
              shortcut="⌘U"
              showTooltip={showTooltips}
            />
            <ActionButton
              icon={Sparkles}
              label="Generate"
              onClick={onGenerateDiagramClick}
              shortcut="⌘G"
              showTooltip={showTooltips}
              variant="primary"
            />
            <ActionButton
              icon={FileText}
              label="Create ADR"
              onClick={onCreateAdrClick}
              shortcut="⌘K"
              showTooltip={showTooltips}
            />
            <ActionButton
              icon={Download}
              label="Export"
              onClick={onExportClick}
              shortcut="⌘E"
              showTooltip={showTooltips}
            />
          </div>

          {/* Mobile: Single menu button */}
          <div className="md:hidden">
            <button
              onClick={onGenerateDiagramClick}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium text-sm"
              aria-label="Generate diagram"
            >
              <Sparkles className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Keyboard shortcuts hint - desktop only */}
      <div className="hidden lg:block px-6 py-1 bg-gray-50 border-t border-gray-100">
        <div className="flex items-center gap-6 text-xs text-gray-500">
          <span>
            <kbd className="px-1.5 py-0.5 bg-white border border-gray-300 rounded text-xs">⌘/</kbd>{" "}
            Toggle sidebar
          </span>
          <span>
            <kbd className="px-1.5 py-0.5 bg-white border border-gray-300 rounded text-xs">⌘[</kbd>{" "}
            Left panel
          </span>
          <span>
            <kbd className="px-1.5 py-0.5 bg-white border border-gray-300 rounded text-xs">⌘]</kbd>{" "}
            Right panel
          </span>
        </div>
      </div>
    </div>
  );
}
