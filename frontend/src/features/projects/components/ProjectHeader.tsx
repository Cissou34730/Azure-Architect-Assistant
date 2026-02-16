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
  readonly onAdrClick?: () => void;
  readonly onExportClick?: () => void;
}

function ProjectHeader({
  onUploadClick,
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
      <div className="sticky top-14 bg-linear-to-r from-brand-soft to-accent-soft border-b border-border z-30 shadow-sm">
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
                allowDelete={true}
              />
            </div>

            <div className="flex items-center gap-2">
              <ProjectHeaderActions
                onAdrClick={onAdrClick}
                onExportClick={onExportClick}
                exportDisabled
              />

              <button
                onClick={handleToggleShortcuts}
                className="p-2 text-secondary hover:text-foreground hover:bg-card rounded-lg transition-colors"
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


