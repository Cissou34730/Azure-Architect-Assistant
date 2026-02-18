import type { Project } from "../../types/agent";

interface ProjectSelectorProps {
  readonly projects: readonly Project[];
  readonly selectedProjectId: string;
  readonly onProjectChange: (projectId: string) => void;
}

export function ProjectSelector({
  projects,
  selectedProjectId,
  onProjectChange,
}: ProjectSelectorProps) {
  return (
    <div className="flex items-center space-x-3">
      <label
        htmlFor="project-select"
        className="text-sm font-medium text-secondary"
      >
        Project Context:
      </label>
      <select
        id="project-select"
        value={selectedProjectId}
        onChange={(e) => {
          onProjectChange(e.target.value);
        }}
        className="flex-1 max-w-md rounded-lg border border-border-stronger px-4 py-2 focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent"
      >
        <option value="">No project (Generic mode)</option>
        {projects.map((project) => (
          <option key={project.id} value={project.id}>
            {project.name}
          </option>
        ))}
      </select>
      {selectedProjectId !== "" && (
        <span className="text-sm text-dim">
          Agent will consider project context in responses
        </span>
      )}
    </div>
  );
}

