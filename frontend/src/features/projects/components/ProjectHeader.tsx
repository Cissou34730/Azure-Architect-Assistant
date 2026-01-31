import { useState, useRef, useCallback, memo } from "react";
import { Command } from "lucide-react";
import { ProjectSelectorDropdown, ProjectSelectorDropdownRef } from "../../../components/common/ProjectSelectorDropdown";
import { DeleteProjectModal } from "../../../components/common/DeleteProjectModal";
import { useProjectSelector } from "../../../hooks/useProjectSelector";
import { Project } from "../../../types/api";
import { useProjectHeaderKeyboard } from "./useProjectHeaderKeyboard";
import { ProjectHeaderShortcuts } from "./ProjectHeaderShortcuts";
import { ProjectHeaderActions } from "./ProjectHeaderActions";
import { useRenderCount } from "../../../hooks/useRenderCount";

interface ProjectHeaderProps {
  readonly onUploadClick?: () => void;
  readonly onGenerateClick?: () => void;
  readonly onAdrClick?: () => void;
  readonly onExportClick?: () => void;
}

function ProjectHeader({
  onUploadClick,
  onGenerateClick,
  onAdrClick,
  onExportClick,
}: ProjectHeaderProps) {
  useRenderCount("ProjectHeader");
  const {
    projects,
    currentProject,
    loading,
    switchProject,
    deleteProject,
    createNewProject,
  } = useProjectSelector();

  const [projectToDelete, setProjectToDelete] = useState<Project | null>(null);
  const projectSelectorRef = useRef<ProjectSelectorDropdownRef>(null);

  const { showShortcuts, setShowShortcuts, shortcuts } = useProjectHeaderKeyboard({
    onUploadClick,
    onGenerateClick,
    projectSelectorRef,
  });

  const handleDeleteRequest = useCallback((project: Project) => {
    setProjectToDelete(project);
  }, []);

  const handleDeleteConfirm = useCallback(async () => {
    if (projectToDelete !== null) {
      await deleteProject(projectToDelete);
      setProjectToDelete(null);
    }
  }, [deleteProject, projectToDelete]);

  const handleToggleShortcuts = useCallback(() => {
    setShowShortcuts((prev) => !prev);
  }, [setShowShortcuts]);

  return (
    <>
      <div className="sticky top-14 bg-linear-to-r from-blue-50 to-indigo-50 border-b border-gray-200 z-30 shadow-sm">
        <div className="max-w-screen-2xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between gap-4">
            <div className="shrink-0">
              <ProjectSelectorDropdown
                ref={projectSelectorRef}
                projects={projects}
                currentProject={currentProject}
                onProjectSelect={switchProject}
                onProjectDelete={handleDeleteRequest}
                onCreateNew={createNewProject}
                loading={loading}
                allowDelete={false}
              />
            </div>

            <div className="flex items-center gap-2">
              <ProjectHeaderActions
                onUploadClick={onUploadClick}
                onGenerateClick={onGenerateClick}
                onAdrClick={onAdrClick}
                onExportClick={onExportClick}
                exportDisabled
              />

              <button
                onClick={handleToggleShortcuts}
                className="p-2 text-gray-600 hover:text-gray-900 hover:bg-white rounded-lg transition-colors"
                title="Keyboard shortcuts (⌘K)"
              >
                <Command className="h-5 w-5" />
              </button>
            </div>
          </div>

          {showShortcuts && <ProjectHeaderShortcuts shortcuts={shortcuts} />}
        </div>
      </div>

      {projectToDelete !== null && (
        <DeleteProjectModal
          project={projectToDelete}
          isOpen
          onClose={() => {
            setProjectToDelete(null);
          }}
          onConfirm={handleDeleteConfirm}
        />
      )}
    </>
  );
}

const projectHeader = memo(ProjectHeader);
export { projectHeader as ProjectHeader };
