import { Project } from "../../../services/apiService";

interface ProjectListProps {
  projects: Project[];
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
    <div className="bg-white rounded-lg shadow p-4">
      <h2 className="text-lg font-semibold mb-4">Projects</h2>

      <form onSubmit={onCreateProject} className="mb-4">
        <input
          type="text"
          value={projectName}
          onChange={(e) => { onProjectNameChange(e.target.value); }}
          placeholder="New project name"
          className="w-full px-3 py-2 border border-gray-300 rounded-md mb-2 text-sm"
        />
        <button
          type="submit"
          disabled={loading}
          className="w-full bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 disabled:opacity-50 text-sm"
        >
          Create Project
        </button>
      </form>

      <div className="space-y-2">
        {projects.map((project) => (
          <button
            key={project.id}
            onClick={() => { onSelectProject(project); }}
            className={`w-full text-left px-3 py-2 rounded-md text-sm ${
              selectedProject?.id === project.id
                ? "bg-blue-100 border border-blue-500"
                : "bg-gray-50 hover:bg-gray-100"
            }`}
          >
            {project.name}
          </button>
        ))}
      </div>
    </div>
  );
}
