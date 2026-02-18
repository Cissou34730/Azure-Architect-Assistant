import { Project } from "../../../types/api";
import { Button } from "../../../components/common";

interface ProjectListProps {
  projects: readonly Project[];
  selectedProject: Project | null;
  onSelectProject: (project: Project) => void;
  projectName: string;
  onProjectNameChange: (name: string) => void;
  onCreateProject: (e: React.FormEvent) => void;
  loading: boolean;
}

export function ProjectList({
  projects,
  selectedProject,
  onSelectProject,
  projectName,
  onProjectNameChange,
  onCreateProject,
  loading,
}: ProjectListProps) {
  return (
    <div className="bg-card rounded-lg shadow p-4">
      <h2 className="text-lg font-semibold mb-4">Projects</h2>

      <form onSubmit={onCreateProject} className="mb-4">
        <input
          type="text"
          value={projectName}
          onChange={(e) => { onProjectNameChange(e.target.value); }}
          placeholder="New project name"
          className="w-full px-3 py-2 border border-border-stronger rounded-md mb-2 text-sm"
        />
        <Button
          type="submit"
          variant="primary"
          disabled={loading}
          className="w-full text-sm"
        >
          Create Project
        </Button>
      </form>

      <div className="space-y-2">
        {projects.map((project) => (
          <button
            key={project.id}
            onClick={() => { onSelectProject(project); }}
            className={`w-full text-left px-3 py-2 rounded-md text-sm ${
              selectedProject?.id === project.id
                ? "bg-brand-soft border border-brand"
                : "bg-surface hover:bg-muted"
            }`}
          >
            {project.name}
          </button>
        ))}
      </div>
    </div>
  );
}


