import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { ProjectList } from "../components/ProjectList";
import { useProjects } from "../hooks/useProjects";

export default function ProjectsPage() {
  const { projects, createProject, loading, fetchProjects } = useProjects();
  const navigate = useNavigate();
  const [newProjectName, setNewProjectName] = useState("");

  useEffect(() => {
    void fetchProjects();
  }, [fetchProjects]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const project = await createProject(newProjectName);
      setNewProjectName("");
      void navigate(`/projects/${project.id}`);
    } catch (error) {
      console.error("Failed to create project:", error);
    }
  };

  return (
    <div className="container mx-auto p-6">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold mb-8 text-gray-900">
          Architecture Projects
        </h1>
        <div className="bg-white rounded-lg shadow p-6">
          <ProjectList
            projects={projects}
            selectedProject={null}
            onSelectProject={(p) => navigate(`/projects/${p.id}`)}
            projectName={newProjectName}
            onProjectNameChange={setNewProjectName}
            onCreateProject={handleCreate}
            loading={loading}
          />
        </div>
      </div>
    </div>
  );
}
