import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { ProjectList } from "../components/ProjectList";
import { useProjects } from "../hooks/useProjects";
import { Card } from "../../../components/common";

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
      void navigate(`/project/${project.id}`);
    } catch (error) {
      console.error("Failed to create project:", error);
    }
  };

  return (
    <div className="container mx-auto p-6">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold mb-8 text-foreground">
          Architecture Projects
        </h1>
        <Card className="p-6">
          <ProjectList
            projects={projects}
            selectedProject={null}
            onSelectProject={(p) => navigate(`/project/${p.id}`)}
            projectName={newProjectName}
            onProjectNameChange={setNewProjectName}
            onCreateProject={handleCreate}
            loading={loading}
          />
        </Card>
      </div>
    </div>
  );
}

