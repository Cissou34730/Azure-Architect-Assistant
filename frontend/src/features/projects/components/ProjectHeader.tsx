import { useState, useRef, useEffect } from "react";
import { Upload, Zap, FileText, Download, Command } from "lucide-react";
import { ProjectSelectorDropdown, ProjectSelectorDropdownRef } from "../../../components/common/ProjectSelectorDropdown";
import { DeleteProjectModal } from "../../../components/common/DeleteProjectModal";
import { useProjectSelector } from "../../../hooks/useProjectSelector";
import { Project } from "../../../types/api";

interface ProjectHeaderProps {
  readonly onUploadClick?: () => void;
  readonly onGenerateClick?: () => void;
  readonly onAdrClick?: () => void;
  readonly onExportClick?: () => void;
}

export function ProjectHeader({
  onUploadClick,
  onGenerateClick,
  onAdrClick,
  onExportClick,
}: ProjectHeaderProps) {
  const {
    projects,
    currentProject,
    loading,
    switchProject,
    deleteProject,
    createNewProject,
  } = useProjectSelector();

  const [projectToDelete, setProjectToDelete] = useState<Project | null>(null);
  const [showShortcuts, setShowShortcuts] = useState(false);
  const projectSelectorRef = useRef<ProjectSelectorDropdownRef>(null);

  // Keyboard shortcut: Cmd/Ctrl+P to open project selector
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "p") {
        e.preventDefault();
        projectSelectorRef.current?.toggle();
      }
      // Cmd/Ctrl+K to show shortcuts
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setShowShortcuts((prev) => !prev);
      }
      // Cmd/Ctrl+U for upload
      if ((e.metaKey || e.ctrlKey) && e.key === "u" && onUploadClick) {
        e.preventDefault();
        onUploadClick();
      }
      // Cmd/Ctrl+G for generate
      if ((e.metaKey || e.ctrlKey) && e.key === "g" && onGenerateClick) {
        e.preventDefault();
        onGenerateClick();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onUploadClick, onGenerateClick]);

  const handleDeleteRequest = (project: Project) => {
    setProjectToDelete(project);
  };

  const handleDeleteConfirm = async () => {
    if (projectToDelete) {
      await deleteProject(projectToDelete);
      setProjectToDelete(null);
    }
  };

  const shortcuts = [
    { key: "⌘P", label: "Switch Project", action: () => projectSelectorRef.current?.open() },
    { key: "⌘U", label: "Upload", action: onUploadClick, visible: !!onUploadClick },
    { key: "⌘G", label: "Generate", action: onGenerateClick, visible: !!onGenerateClick },
    { key: "⌘K", label: "Shortcuts", action: () => setShowShortcuts(!showShortcuts) },
  ].filter((s) => s.visible !== false);

  return (
    <>
      <div className="sticky top-14 bg-linear-to-r from-blue-50 to-indigo-50 border-b border-gray-200 z-30 shadow-sm">
        <div className="max-w-[1920px] mx-auto px-6 py-4">
          <div className="flex items-center justify-between gap-4">
            {/* Left: Project Selector */}
            <div className="shrink-0">
              <ProjectSelectorDropdown
                ref={projectSelectorRef}
                projects={projects}
                currentProject={currentProject}
                onProjectSelect={switchProject}
                onProjectDelete={handleDeleteRequest}
                onCreateNew={createNewProject}
                loading={loading}
              />
            </div>

            {/* Right: Action Buttons */}
            <div className="flex items-center gap-2">
              {onUploadClick && (
                <button
                  onClick={onUploadClick}
                  className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors shadow-sm"
                  title="Upload documents (⌘U)"
                >
                  <Upload className="h-4 w-4" />
                  <span className="hidden sm:inline">Upload</span>
                </button>
              )}

              {onGenerateClick && (
                <button
                  onClick={onGenerateClick}
                  className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors shadow-sm"
                  title="Generate architecture (⌘G)"
                >
                  <Zap className="h-4 w-4" />
                  <span className="hidden sm:inline">Generate</span>
                </button>
              )}

              {onAdrClick && (
                <button
                  onClick={onAdrClick}
                  className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors shadow-sm"
                  title="Create ADR"
                >
                  <FileText className="h-4 w-4" />
                  <span className="hidden sm:inline">ADR</span>
                </button>
              )}

              {onExportClick && (
                <button
                  onClick={onExportClick}
                  className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors shadow-sm"
                  title="Export"
                >
                  <Download className="h-4 w-4" />
                  <span className="hidden sm:inline">Export</span>
                </button>
              )}

              {/* Shortcuts Toggle */}
              <button
                onClick={() => setShowShortcuts(!showShortcuts)}
                className="p-2 text-gray-600 hover:text-gray-900 hover:bg-white rounded-lg transition-colors"
                title="Keyboard shortcuts (⌘K)"
              >
                <Command className="h-5 w-5" />
              </button>
            </div>
          </div>

          {/* Shortcuts Overlay */}
          {showShortcuts && (
            <div className="mt-3 p-3 bg-white rounded-lg border border-gray-200 shadow-md animate-in fade-in slide-in-from-top-2 duration-200">
              <h3 className="text-xs font-semibold text-gray-700 mb-2">Keyboard Shortcuts</h3>
              <div className="grid grid-cols-2 gap-2">
                {shortcuts.map((shortcut) => (
                  <div key={shortcut.key} className="flex items-center justify-between text-xs">
                    <span className="text-gray-600">{shortcut.label}</span>
                    <kbd className="px-2 py-1 bg-gray-100 border border-gray-300 rounded text-gray-700 font-mono">
                      {shortcut.key}
                    </kbd>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      {projectToDelete && (
        <DeleteProjectModal
          project={projectToDelete}
          isOpen={!!projectToDelete}
          onClose={() => setProjectToDelete(null)}
          onConfirm={handleDeleteConfirm}
        />
      )}
    </>
  );
}
