import { useParams, Outlet } from "react-router-dom";
import { useState, useEffect } from "react";
import { useProjectDetails } from "../hooks/useProjectDetails";
import { ErrorBoundary } from "../../../components/common";
import { ProjectProvider } from "../context/ProjectProvider";
import { CommandPalette } from "../components/common/CommandPalette";

export default function ProjectDetailPage() {
  const { projectId } = useParams();
  const projectDetails = useProjectDetails(projectId);
  const { selectedProject, loading } = projectDetails;
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false);

  // Global keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Cmd/Ctrl + K: Open command palette
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setIsCommandPaletteOpen(true);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => { window.removeEventListener("keydown", handleKeyDown); };
  }, []);

  if (selectedProject === null && loading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" />
      </div>
    );
  }

  if (selectedProject === null) {
    return (
      <div className="container mx-auto p-6 text-center">
        <h2 className="text-xl font-semibold text-gray-800">
          Project not found
        </h2>
        <p className="text-gray-600 mt-2">
          The requested project could not be found.
        </p>
      </div>
    );
  }

  // Unified layout only.
  return (
    <ErrorBoundary>
      <ProjectProvider value={projectDetails}>
        {/* Outlet renders the unified project workspace. */}
        <Outlet />

        {/* Command Palette - Available globally */}
        <CommandPalette
          isOpen={isCommandPaletteOpen}
          onClose={() => { setIsCommandPaletteOpen(false); }}
        />
      </ProjectProvider>
    </ErrorBoundary>
  );
}
