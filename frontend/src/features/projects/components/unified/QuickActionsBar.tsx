import { Upload, Sparkles, FileText, Download, Menu } from "lucide-react";
import { useState } from "react";

interface QuickActionsBarProps {
  projectName: string;
  onUploadClick: () => void;
  onGenerateDiagramClick: () => void;
  onCreateAdrClick: () => void;
  onExportClick: () => void;
  onMenuClick?: () => void;
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
        <div className="flex items-center gap-4">
          {onMenuClick && (
            <button
              onClick={onMenuClick}
              className="lg:hidden p-2 hover:bg-gray-100 rounded-lg transition-colors"
              title="Toggle menu"
            >
              <Menu className="h-5 w-5 text-gray-700" />
            </button>
          )}
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded-lg bg-linear-to-br from-blue-500 to-blue-600 flex items-center justify-center shrink-0">
              <span className="text-white font-semibold text-sm">
                {projectName.charAt(0).toUpperCase()}
              </span>
            </div>
            <div>
              <h1 className="text-lg font-semibold text-gray-900 leading-tight">
                {projectName}
              </h1>
              <p className="text-xs text-gray-500">Architecture Workspace</p>
            </div>
          </div>
        </div>

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

interface ActionButtonProps {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  onClick: () => void;
  shortcut?: string;
  showTooltip?: boolean;
  variant?: "default" | "primary";
}

function ActionButton({
  icon: Icon,
  label,
  onClick,
  shortcut,
  showTooltip,
  variant = "default",
}: ActionButtonProps) {
  const baseClasses = "flex items-center gap-2 px-4 py-2 rounded-lg transition-all font-medium text-sm";
  const variantClasses =
    variant === "primary"
      ? "bg-blue-600 text-white hover:bg-blue-700 shadow-sm"
      : "bg-gray-100 text-gray-700 hover:bg-gray-200";

  return (
    <button
      onClick={onClick}
      className={`${baseClasses} ${variantClasses}`}
      title={showTooltip && shortcut ? `${label} (${shortcut})` : label}
    >
      <Icon className="h-4 w-4" />
      <span className="hidden lg:inline">{label}</span>
      {shortcut && (
        <kbd className="hidden xl:inline-block px-1.5 py-0.5 bg-white/10 border border-white/20 rounded text-xs">
          {shortcut}
        </kbd>
      )}
    </button>
  );
}
